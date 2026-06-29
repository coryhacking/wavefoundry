#!/usr/bin/env python3
"""Shared readers and helpers for the local dashboard server."""
from __future__ import annotations

import json
import os
import re
import sys
import time
import contextlib
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import server
import subprocess_util  # shared subprocess isolation (wave 1p8gu)


_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_OWNER_RE = re.compile(r"^Owner:\s+(.+)$", re.MULTILINE)
_WAVE_RE = re.compile(r"^Wave:\s+`([^`]+)`", re.MULTILINE)
_SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
# Wave 1p31b (1p32k): include `~` as a valid checkbox mark for intentionally-deferred
# tasks and ACs. The dashboard renders `[~]` as a distinct third state (not done, not
# pending) and excludes `[~]` items from progress denominators.
_TASK_RE = re.compile(r"^\s*-\s+(?:(?:\[(?P<mark>[ xX~])\])\s+)?(?P<label>.+?)\s*$", re.MULTILINE)
_ACTIVE_WAVE_RE = re.compile(r"^\*\*Active wave:\*\*\s+(.+)$", re.MULTILINE)
DASHBOARD_START_LOCK_NAME = "dashboard-start.lock"
DASHBOARD_SERVER_LOCK_NAME = "dashboard-server.lock"
GRAPH_DIRNAME = "graph"
# Wave 1p4ww: single project graph — the framework graph layer was removed.
GRAPH_FILENAMES = {
    "project": "project-graph.json",
}
GRAPH_CLUSTER_FILENAMES = {
    "project": "project-graph-clusters.json",
}


class DashboardLockBusy(RuntimeError):
    """Raised when another process holds a dashboard coordination lock."""


def discover_root(override: str | None = None) -> Path:
    """Discover the project root for dashboard reads."""
    if override:
        return Path(override).expanduser().resolve()
    for env_key in ("PROJECT_ROOT", "REPO_ROOT"):
        raw = os.environ.get(env_key)
        if not raw:
            continue
        candidate = Path(raw).expanduser().resolve()
        if (candidate / "docs" / "workflow-config.json").is_file():
            return candidate
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / "docs" / "workflow-config.json").is_file():
            return candidate
    sys.stderr.write(
        "[dashboard] WARNING: no workflow-config.json found; using cwd as project root.\n"
    )
    return cwd


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _lance_table_stats(index_dir: Path | None) -> tuple[int, int, set[str]]:
    """Return (doc_chunks, code_chunks, files) from Lance tables when available."""
    if index_dir is None:
        return 0, 0, set()
    doc_chunks = 0
    code_chunks = 0
    files: set[str] = set()
    docs_lance = index_dir / "docs.lance"
    code_lance = index_dir / "code.lance"
    if not docs_lance.is_dir() and not code_lance.is_dir():
        return 0, 0, set()
    try:
        import lancedb
        db = lancedb.connect(str(index_dir))
        if docs_lance.is_dir():
            docs = db.open_table("docs")
            doc_chunks = docs.count_rows()
            try:
                docs_df = docs.to_pandas()
                if "path" in docs_df:
                    files.update(str(path) for path in docs_df["path"].tolist() if path)
            except Exception:
                pass
        if code_lance.is_dir():
            code = db.open_table("code")
            code_chunks = code.count_rows()
            try:
                code_df = code.to_pandas()
                if "path" in code_df:
                    files.update(str(path) for path in code_df["path"].tolist() if path)
            except Exception:
                pass
    except Exception:
        return 0, 0, set()
    files.discard("")
    return doc_chunks, code_chunks, files


def read_workflow_config(root: Path) -> dict[str, Any]:
    cfg = _read_json(root / "docs" / "workflow-config.json", {})
    return cfg if isinstance(cfg, dict) else {}


def read_repo_profile(root: Path) -> dict[str, Any]:
    data = _read_json(root / "docs" / "repo-profile.json", {})
    return data if isinstance(data, dict) else {}


def read_prompt_manifest(root: Path) -> dict[str, Any]:
    data = _read_json(root / "docs" / "prompts" / "prompt-surface-manifest.json", {})
    return data if isinstance(data, dict) else {}


def read_dashboard_config(root: Path) -> dict[str, Any]:
    cfg = read_workflow_config(root).get("dashboard", {})
    if not isinstance(cfg, dict):
        cfg = {}
    preferred = cfg.get("preferred_port")
    start = cfg.get("port_range_start", preferred if isinstance(preferred, int) else 43127)
    end = cfg.get("port_range_end", start + 20 if isinstance(start, int) else 43147)
    return {
        "enabled": bool(cfg.get("enabled", True)),
        "entrypoint": str(cfg.get("entrypoint", "dashboard.html")).strip() or "dashboard.html",
        "preferred_port": preferred if isinstance(preferred, int) else 43127,
        "port_range_start": start if isinstance(start, int) else 43127,
        "port_range_end": end if isinstance(end, int) else 43147,
        "poll_interval_ms": int(cfg.get("poll_interval_ms", 2000) or 2000),
        "host": str(cfg.get("host", "127.0.0.1")).strip() or "127.0.0.1",
        "project_label": str(cfg.get("project_label", "")).strip(),
        "terminology": cfg.get("terminology", {}) if isinstance(cfg.get("terminology"), dict) else {},
        "include_dirs": [str(d) for d in cfg.get("include_dirs", []) if isinstance(d, str)] if isinstance(cfg.get("include_dirs"), list) else [],
        # 1p7it: the dashboard is a read-only viewer — index updates are owned by the MCP/hook
        # background path (post-edit hook + the MCP server's background refresh + wave_index_build),
        # never the dashboard. The former `auto_index` / `auto_index_delay_seconds` settings were removed.
    }


def dashboard_metadata_path(root: Path) -> Path:
    # Wave 1p64x: the server lock file IS the startup-metadata store — one sidecar,
    # not two. `flock` is advisory and per-open-file-description, so the lock holder
    # can rewrite this file's content in place (see write_dashboard_metadata) while
    # keeping its lifetime lock. (Was a separate `dashboard-server.json`.)
    return root / ".wavefoundry" / DASHBOARD_SERVER_LOCK_NAME


def dashboard_lock_path(root: Path, name: str) -> Path:
    return root / ".wavefoundry" / name


@contextlib.contextmanager
def dashboard_lock(root: Path, name: str):
    """Acquire a non-blocking OS lock for dashboard process coordination."""
    lock_path = dashboard_lock_path(root, name)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = lock_path.open("a+", encoding="utf-8")
    acquired = False
    try:
        if os.name == "nt":
            import msvcrt
            try:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                acquired = True
            except OSError as exc:
                raise DashboardLockBusy(f"Dashboard lock busy: {lock_path}") from exc
        else:
            import fcntl
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except BlockingIOError as exc:
                raise DashboardLockBusy(f"Dashboard lock busy: {lock_path}") from exc

        fh.seek(0)
        fh.truncate()
        fh.write(json.dumps({"pid": os.getpid(), "started_at": time.time(), "lock": name}))
        fh.flush()
        yield
    finally:
        if acquired:
            try:
                if os.name == "nt":
                    import msvcrt
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        fh.close()


def dashboard_start_lock(root: Path):
    return dashboard_lock(root, DASHBOARD_START_LOCK_NAME)


def dashboard_server_lock(root: Path):
    return dashboard_lock(root, DASHBOARD_SERVER_LOCK_NAME)


def read_dashboard_metadata(root: Path) -> dict[str, Any]:
    data = _read_json(dashboard_metadata_path(root), {})
    return data if isinstance(data, dict) else {}


def write_dashboard_metadata(root: Path, payload: dict[str, Any]) -> None:
    # Wave 1p64x: this writes the server LOCK file's content (the lock and the
    # metadata are one file). The write MUST stay an in-place truncate-write — do
    # NOT switch to a temp-file + os.replace/rename: a rename points the path at a
    # new inode, orphaning the lifetime `flock` the running server holds on the old
    # inode, which would let a second server acquire the lock and run concurrently.
    # In-place truncate keeps the holder's per-open-file-description lock intact.
    path = dashboard_metadata_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _windows_process_cmdlines() -> str | None:
    """Wave 1p6eq: best-effort ``<pid> <command line>`` listing on native Windows, one process per
    line, via PowerShell + CIM (``Get-CimInstance Win32_Process`` — the only built-in that exposes a
    process's full CommandLine; ``tasklist`` does not). Pre-filtered to dashboard_server.py. Returns
    None on ANY failure so the caller falls back to bare recorded-PID liveness (no regression).
    FORWARD-COMPAT: unverified on a real Windows host (native Windows is Area-1) — Windows-smoke-deferred.
    """
    ps_script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -and $_.CommandLine -like '*dashboard_server.py*' } | "
        "ForEach-Object { \"$($_.ProcessId) $($_.CommandLine)\" }"
    )
    try:
        result = subprocess_util.isolated_run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True, text=True, check=False, timeout=10,
        )
    except Exception:  # noqa: BLE001 — best-effort; any failure → fall back to bare-PID liveness
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def dashboard_cmdline_pids(root: Path) -> list[int] | None:
    """Live `dashboard_server.py --root <root>` PIDs, by process-cmdline scan (1p654).

    Reconciliation against actual processes — not just the recorded-PID metadata —
    so a drifted/removed metadata file can't hide an orphaned dashboard, and a
    recycled/zombie PID can't masquerade as the running server. Uses `ps` on POSIX
    and a best-effort PowerShell/CIM scan on native Windows (1p6eq); returns ``None``
    when a scan is unavailable/failed (PowerShell or `ps` error) so callers fall back
    to the bare liveness check (no regression).
    Matches ONLY processes whose `--root` resolves to this exact root; the current
    process is excluded. Shared home (1p654 review follow-up): consumed by both the
    server lifecycle (server_impl) and upgrade dashboard detection.
    """
    # Wave 1p6eq: native Windows now gets a cmdline scan too (was `return None`, which disabled the
    # 1p654 orphan reconciliation on Windows). Best-effort — the helper returns None on any failure,
    # so the isinstance guard below falls back to bare recorded-PID liveness (no regression).
    if os.name == "nt":
        out = _windows_process_cmdlines()
    else:
        try:
            out = subprocess_util.isolated_run(
                ["ps", "-axww", "-o", "pid=,command="],
                capture_output=True, text=True, check=False,
            ).stdout
        except Exception:  # noqa: BLE001 — best-effort scan; any failure → fall back
            return None
    if not isinstance(out, str):
        return None
    try:
        target = Path(root).resolve()
    except OSError:
        target = Path(root)
    self_pid = os.getpid()
    pids: list[int] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or "dashboard_server.py" not in line:
            continue
        head, _, rest = line.partition(" ")
        try:
            pid = int(head)
        except ValueError:
            continue
        if pid == self_pid:
            continue
        toks = rest.split()
        matched = False
        for i, tok in enumerate(toks):
            cand: str | None = None
            if tok == "--root" and i + 1 < len(toks):
                cand = toks[i + 1]
            elif tok.startswith("--root="):
                cand = tok[len("--root="):]
            if cand is None:
                continue
            try:
                if Path(cand).resolve() == target:
                    matched = True
                    break
            except OSError:
                if cand == str(target):
                    matched = True
                    break
        if matched:
            pids.append(pid)
    return pids


def graph_path(root: Path, layer: str = "project") -> Path:
    if layer not in GRAPH_FILENAMES:
        raise ValueError(f"Unsupported graph layer: {layer}")
    return root / ".wavefoundry" / "index" / GRAPH_DIRNAME / GRAPH_FILENAMES[layer]


def graph_cluster_path(root: Path, layer: str = "project") -> Path:
    if layer not in GRAPH_CLUSTER_FILENAMES:
        raise ValueError(f"Unsupported graph layer: {layer}")
    return root / ".wavefoundry" / "index" / GRAPH_DIRNAME / GRAPH_CLUSTER_FILENAMES[layer]


def read_graph_cluster_payload(root: Path, layer: str) -> dict[str, Any]:
    path = graph_cluster_path(root, layer)
    data = _read_json(path, {})
    if isinstance(data, dict) and data:
        data.setdefault("layer", layer)
        data.setdefault("cluster_schema_version", "1")
        data.setdefault("communities", [])
        data.setdefault("community_count", len(data.get("communities") or []))
        try:
            data["cluster_mtime"] = path.stat().st_mtime_ns
        except OSError:
            data["cluster_mtime"] = 0
        data["present"] = True
        data["cluster_path"] = str(path.relative_to(root)).replace("\\", "/")
        return data
    return {
        "layer": layer,
        "cluster_schema_version": "1",
        "cluster_mtime": 0,
        "present": False,
        "cluster_path": str(path.relative_to(root)).replace("\\", "/"),
        "communities": [],
        "community_count": 0,
    }


def _enrich_graph_nodes_for_dashboard(data: dict[str, Any]) -> None:
    """Attach server-computed degree and community_id for dashboard rendering (12yro)."""
    nodes = data.get("nodes")
    edges = data.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return
    degree: dict[str, int] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("source") or "")
        tgt = str(edge.get("target") or "")
        if src:
            degree[src] = degree.get(src, 0) + 1
        if tgt:
            degree[tgt] = degree.get(tgt, 0) + 1
    community_by_node: dict[str, str] = {}
    clusters = data.get("clusters") if isinstance(data.get("clusters"), dict) else {}
    for cluster in clusters.get("communities") or []:
        if not isinstance(cluster, dict):
            continue
        community_id = str(cluster.get("community_id") or "").strip()
        if not community_id:
            continue
        for node_id in cluster.get("node_ids") or []:
            community_by_node[str(node_id)] = community_id
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "")
        node["degree"] = int(degree.get(node_id, 0))
        if node.get("community_id") is None and node_id in community_by_node:
            node["community_id"] = community_by_node[node_id]


def read_graph_payload(root: Path, layer: str) -> dict[str, Any]:
    path = graph_path(root, layer)
    data = _read_json(path, {})
    if isinstance(data, dict) and data:
        data.setdefault("layer", layer)
        data.setdefault("schema_version", "1")
        data.setdefault("nodes", [])
        data.setdefault("edges", [])
        data.setdefault("counts", {"files": 0, "nodes": len(data.get("nodes") or []), "edges": len(data.get("edges") or [])})
        cluster_data = read_graph_cluster_payload(root, layer)
        try:
            data["graph_mtime"] = path.stat().st_mtime_ns
        except OSError:
            data["graph_mtime"] = 0
        data["cluster_mtime"] = int(cluster_data.get("cluster_mtime") or 0)
        data["graph_version"] = max(int(data.get("graph_mtime") or 0), int(data.get("cluster_mtime") or 0))
        data["clusters"] = cluster_data
        data["present"] = True
        data["graph_path"] = str(path.relative_to(root)).replace("\\", "/")
        _enrich_graph_nodes_for_dashboard(data)
        return data
    return {
        "layer": layer,
        "schema_version": "1",
        "graph_mtime": 0,
        "cluster_mtime": 0,
        "graph_version": 0,
        "present": False,
        "graph_path": str(path.relative_to(root)).replace("\\", "/"),
        "nodes": [],
        "edges": [],
        "counts": {"files": 0, "nodes": 0, "edges": 0},
        "clusters": {
            "layer": layer,
            "cluster_schema_version": "1",
            "cluster_mtime": 0,
            "present": False,
            "cluster_path": str(graph_cluster_path(root, layer).relative_to(root)).replace("\\", "/"),
            "communities": [],
            "community_count": 0,
        },
    }


def dashboard_browser_open_enabled() -> bool:
    """Return False when the dashboard must not open a browser (tests, CI, operator opt-out).

    Set ``WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER=1`` (``run_tests.py`` and ``tests/__init__``
  do this automatically). Use ``=0`` to force enable inside a test that asserts browser open.
    """
    val = os.environ.get("WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER", "").strip().lower()
    if val in ("0", "false", "no", "off"):
        return True
    if val in ("1", "true", "yes", "on"):
        return False
    return True


def read_framework_version(root: Path) -> str:
    version_path = root / ".wavefoundry" / "framework" / "VERSION"
    if not version_path.exists():
        return ""
    try:
        return version_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def read_readme_title(root: Path) -> str:
    readme = root / "README.md"
    if not readme.exists():
        return ""
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return ""
    m = _TITLE_RE.search(text)
    return m.group(1).strip() if m else ""


def derive_project_name(root: Path) -> str:
    dashboard_cfg = read_dashboard_config(root)
    if dashboard_cfg["project_label"]:
        return dashboard_cfg["project_label"]
    profile = read_repo_profile(root)
    explicit = profile.get("project_name")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    readme_title = read_readme_title(root)
    if readme_title:
        return readme_title
    return root.name


def _extract_section(text: str, heading: str) -> str:
    heading_re = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = heading_re.search(text)
    if not match:
        return ""
    body = text[match.end() :].lstrip("\r\n")
    end_match = re.search(r"(?m)^##\s+", body)
    section = body[: end_match.start()] if end_match else body
    return section.strip()


def _markdown_table_rows(section_text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in section_text.splitlines():
        line = raw.strip()
        if not line.startswith("|") or line.count("|") < 2:
            continue
        if set(line.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(cells)
    return rows


_AC_ID_RE = re.compile(r"(AC-[\w\-]+)")
_TERMINAL_CHANGE_STATUSES = {"complete", "completed", "closed"}


def _parse_ac_priority_counts(section_text: str) -> dict[str, int]:
    counts = {
        "required": 0,
        "important": 0,
        "nice-to-have": 0,
        "not-this-scope": 0,
        "unknown": 0,
    }
    rows = _markdown_table_rows(section_text)
    for row in rows[1:]:
        if len(row) < 2:
            continue
        value = row[1].strip().lower()
        if value in counts:
            counts[value] += 1
        elif value.replace(" ", "-") in counts:
            counts[value.replace(" ", "-")] += 1
        else:
            counts["unknown"] += 1
    return counts


def _is_terminal_change_status(status: str) -> bool:
    return status.strip().lower() in _TERMINAL_CHANGE_STATUSES


def _parse_progress_log(section_text: str) -> list[dict[str, str]]:
    rows = _markdown_table_rows(section_text)
    if len(rows) < 2:
        return []
    headers = [h.strip().lower() for h in rows[0]]
    result: list[dict[str, str]] = []
    for row in rows[1:]:
        if len(row) != len(headers):
            continue
        result.append({headers[i]: row[i] for i in range(len(headers))})
    return result


def _parse_tasks(tasks_section: str, change_status: str) -> dict[str, Any]:
    tasks = []
    completed = 0
    deferred = 0
    for match in _TASK_RE.finditer(tasks_section):
        mark = (match.group("mark") or "").strip().lower()
        # Wave 1p31b (1p32k): `[~]` = intentionally deferred. Wave 1p458 (1p45a): deferred
        # tasks stay in the denominator and read as outstanding while the wave is open;
        # they fold into done only once the wave is closed (see the progress builder).
        is_deferred = mark == "~"
        done = (mark == "x") if mark else _is_terminal_change_status(change_status)
        if is_deferred:
            deferred += 1
        elif done:
            completed += 1
        tasks.append({
            "label": match.group("label").strip(),
            "done": done,
            "deferred": is_deferred,
        })
    # `completed` is `[x]`-only (the open-wave reading); `deferred` is tracked for the
    # detail-dialog marker but no longer subtracted from `total`.
    total = len(tasks)
    return {
        "total": total,
        "completed": completed,
        "open": max(0, total - completed),
        "deferred": deferred,
        "items": tasks,
    }


_AC_LINE_RE = re.compile(r"^\s*(?:-|\d+\.)\s+(?:(?:\[(?P<mark>[ xX~])\])\s+)?(?P<text>.+?)\s*$", re.MULTILINE)


def _parse_ac_items(ac_section: str, priority_section: str, change_status: str) -> list[dict[str, Any]]:
    """Return individual AC items with text, completion status, deferred status, and priority.

    Wave 1p31b (1p32k): `[~]` ACs are marked ``deferred=True``. They are neither done
    nor pending — they are intentionally out of scope (operator direction, reconsidered
    requirement, or genuine scope-narrowing during implementation). The dashboard
    excludes them from progress denominators so a fully-met change with `[~]` ACs renders
    as complete rather than as incomplete-by-the-deferred-count.
    """
    priority_rows: list[str] = []
    priority_map: dict[str, str] = {}
    for row in _markdown_table_rows(priority_section)[1:]:
        if len(row) >= 2:
            ac_id = row[0].strip()
            priority = row[1].strip().lower().replace(" ", "-")
            priority_rows.append(priority)
            priority_map[ac_id] = priority

    items = []
    for index, match in enumerate(_AC_LINE_RE.finditer(ac_section)):
        mark = (match.group("mark") or "").strip().lower()
        is_deferred = mark == "~"
        done = (mark == "x") if mark else _is_terminal_change_status(change_status)
        text = match.group("text").strip()
        id_match = _AC_ID_RE.search(text)
        ac_id = id_match.group(1) if id_match else ""
        priority = priority_map.get(ac_id)
        if priority is None and index < len(priority_rows):
            priority = priority_rows[index]
        if priority is None:
            priority = "unknown"
        items.append({
            "id": ac_id,
            "text": text,
            "done": done and not is_deferred,
            "deferred": is_deferred,
            "priority": priority,
        })
    return items


def _completed_ac_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {"required": 0, "important": 0, "nice-to-have": 0, "not-this-scope": 0, "unknown": 0}
    for item in items:
        if item.get("deferred"):
            continue
        if not item.get("done"):
            continue
        priority = str(item.get("priority") or "unknown")
        counts[priority] = counts.get(priority, 0) + 1
    return counts


def _deferred_ac_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    """Wave 1p31b (1p32k): per-priority counts of `[~]` (intentionally-deferred) ACs."""
    counts: dict[str, int] = {"required": 0, "important": 0, "nice-to-have": 0, "not-this-scope": 0, "unknown": 0}
    for item in items:
        if not item.get("deferred"):
            continue
        priority = str(item.get("priority") or "unknown")
        counts[priority] = counts.get(priority, 0) + 1
    return counts


def _sum_change_ac_counts(changes: list[dict[str, Any]], key: str) -> int:
    return sum(sum(int(v) for v in (c.get(key) or {}).values()) for c in changes)


def _visible_ac_items(change: dict[str, Any]) -> list[dict[str, Any]]:
    items = change.get("ac_items") or []
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict) and item.get("priority") != "not-this-scope"]


def _sum_visible_ac_counts(changes: list[dict[str, Any]]) -> tuple[int, int]:
    total = 0
    done = 0
    for change in changes:
        for item in _visible_ac_items(change):
            total += 1
            if item.get("done"):
                done += 1
    return total, done


def _sum_change_task_counts(changes: list[dict[str, Any]], key: str) -> int:
    return sum(int(c.get(key) or 0) for c in changes)


def _wave_only_metric_counts(
    waves: list[dict[str, Any]],
    wave_changes: list[dict[str, Any]],
    plan_changes: list[dict[str, Any]],
    current_wave_id: str | None,
) -> dict[str, Any]:
    active_wave_ids = {wave["wave_id"] for wave in waves if wave.get("status") == "active"}
    if active_wave_ids:
        active_changes = [c for c in wave_changes if c.get("wave_id") in active_wave_ids]
        current_wave_changes = [c for c in active_changes if c.get("wave_id") == current_wave_id] if current_wave_id else active_changes
        scope = "active_wave"
    else:
        pending_wave_ids = {
            wave["wave_id"]
            for wave in waves
            if wave.get("status") not in {"active", "closed", "completed"}
        }
        current_wave_changes = [
            *[c for c in wave_changes if c.get("wave_id") in pending_wave_ids],
            *plan_changes,
        ]
        scope = "pending_changes"

    closed_wave_ids = {wave["wave_id"] for wave in waves if wave.get("status") in {"closed", "completed"}}

    change_total = len(current_wave_changes)
    change_done = sum(
        1 for c in current_wave_changes
        if _is_terminal_change_status(str(c.get("status") or "")) or c.get("wave_id") in closed_wave_ids
    )
    task_total = _sum_change_task_counts(current_wave_changes, "tasks_total")
    task_done = sum(
        int(c.get("tasks_total") or 0) if c.get("wave_id") in closed_wave_ids
        else int(c.get("tasks_completed") or 0)
        for c in current_wave_changes
    )
    ac_total = 0
    ac_done = 0
    ac_deferred = 0
    for c in current_wave_changes:
        items = _visible_ac_items(c)
        # Wave 1p458 (1p45a): `[~]` deferred ACs stay IN the denominator. While the wave is
        # open they read as outstanding (not done); once the wave is closed every in-scope
        # item — including deferred — counts as done. `ac_deferred` is retained as an
        # informational count for the detail-dialog marker, not subtracted from totals.
        # (`_visible_ac_items` already drops `not-this-scope`, so a `[~]` not-this-scope AC
        # is excluded from both total and done.)
        ac_deferred += sum(1 for item in items if item.get("deferred"))
        ac_total += len(items)
        if c.get("wave_id") in closed_wave_ids:
            ac_done += len(items)
        else:
            ac_done += sum(1 for item in items if item.get("done"))

    return {
        "changes": {
            "total": change_total,
            "done": change_done,
            "pending": max(0, change_total - change_done),
        },
        "tasks": {
            "total": task_total,
            "done": task_done,
            "pending": max(0, task_total - task_done),
        },
        "acs": {
            "total": ac_total,
            "done": ac_done,
            "pending": max(0, ac_total - ac_done),
            "deferred": ac_deferred,
        },
        "scope": scope,
    }


def _parse_participants(section_text: str) -> list[dict[str, str]]:
    rows = _markdown_table_rows(section_text)
    if len(rows) < 2:
        return []
    result: list[dict[str, str]] = []
    for row in rows[1:]:
        if len(row) < 3:
            continue
        result.append({"role": row[0], "lane": row[1], "scope": row[2]})
    return result


def _parse_review_evidence(section_text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for raw in section_text.splitlines():
        line = raw.strip()
        if not line.startswith("- "):
            continue
        body = line[2:]
        key, _, value = body.partition(":")
        items.append({"key": key.strip(), "value": value.strip()})
    return items


@dataclass
class ChangeRecord:
    change_id: str
    title: str
    description: str
    status: str
    path: str
    scope: str
    wave_id: str | None
    kind: str
    owner: str
    tasks_total: int
    tasks_completed: int
    tasks_deferred: int  # Wave 1p31b (1p32k): count of `[~]` tasks intentionally deferred
    tasks_items: list[dict[str, Any]]
    ac_priority_counts: dict[str, int]
    ac_completed_counts: dict[str, int]
    ac_deferred_counts: dict[str, int]  # Wave 1p31b (1p32k): per-priority counts of `[~]` ACs
    ac_items: list[dict[str, Any]]
    latest_progress: dict[str, str] | None
    progress_log: list[dict[str, str]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.progress_log is None:
            self.progress_log = []


def parse_change_doc(root: Path, change_path: Path) -> ChangeRecord:
    try:
        text = change_path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    change_match = server._CHANGE_ID_PATTERN.search(text)
    # Accept both "Change Status: `value`" (canonical) and plain "Status: value" (fallback for
    # projects that omit the "Change" prefix and backticks).
    status_match = server._CHANGE_STATUS_PATTERN.search(text) or server._STATUS_PATTERN.search(text)
    title_match = _TITLE_RE.search(text)
    owner_match = _OWNER_RE.search(text)
    wave_match = _WAVE_RE.search(text)
    change_id = change_match.group(1) if change_match else change_path.stem
    change_status = status_match.group(1) if status_match else "unknown"
    title = title_match.group(1).strip() if title_match else change_path.stem
    owner = owner_match.group(1).strip() if owner_match else "unknown"
    wave_id = wave_match.group(1) if wave_match else (change_path.parent.name if change_path.parent.name != "plans" else None)
    kind = change_id.split("-", 1)[1].split(" ", 1)[0] if "-" in change_id and " " in change_id else "change"
    rationale = _extract_section(text, "Rationale")
    _first_para = next((ln.strip() for ln in rationale.splitlines() if ln.strip()), "")
    _sent_end = _first_para.find(". ")
    description = _first_para[: _sent_end + 1] if _sent_end != -1 else _first_para
    ac_priority_section = _extract_section(text, "AC Priority")
    ac_section = _extract_section(text, "Acceptance Criteria")
    tasks_section = _extract_section(text, "Tasks")
    ac_counts = _parse_ac_priority_counts(ac_priority_section)
    ac_items = _parse_ac_items(ac_section, ac_priority_section, change_status)
    ac_completed = _completed_ac_counts(ac_items)
    ac_deferred = _deferred_ac_counts(ac_items)
    tasks = _parse_tasks(tasks_section, change_status)
    progress = _parse_progress_log(_extract_section(text, "Progress Log"))
    latest = progress[-1] if progress else None
    scope = "wave" if "docs/waves/" in str(change_path).replace("\\", "/") else "plan"
    return ChangeRecord(
        change_id=change_id,
        title=title,
        description=description,
        status=change_status,
        path=str(change_path.relative_to(root)).replace("\\", "/"),
        scope=scope,
        wave_id=wave_id,
        kind=kind,
        owner=owner,
        tasks_total=tasks["total"],
        tasks_completed=tasks["completed"],
        tasks_deferred=tasks.get("deferred", 0),
        tasks_items=tasks["items"],
        ac_priority_counts=ac_counts,
        ac_completed_counts=ac_completed,
        ac_deferred_counts=ac_deferred,
        ac_items=ac_items,
        latest_progress=latest,
        progress_log=progress,
    )


def collect_changes(root: Path) -> dict[str, list[dict[str, Any]]]:
    wave_changes: list[dict[str, Any]] = []
    plan_changes: list[dict[str, Any]] = []

    for wave in server.list_waves(root):
        wave_md = Path(wave["path"])
        for change in wave.get("changes", []):
            change_path = wave_md.parent / f"{change['id']}.md"
            if not change_path.exists():
                continue
            record = parse_change_doc(root, change_path)
            wave_changes.append(record.__dict__)

    for plan in server.list_plans(root):
        plan_path = root / plan["path"]
        if not plan_path.exists():
            continue
        record = parse_change_doc(root, plan_path)
        plan_changes.append(record.__dict__)

    return {"wave": wave_changes, "plan": plan_changes}


def collect_waves(root: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for wave in server.list_waves(root):
        wave_md = Path(wave["path"])
        try:
            text = wave_md.read_text(encoding="utf-8")
        except OSError:
            continue
        title_match = re.search(r"^Title:\s+(.+)$", text, re.MULTILINE)
        objective = _extract_section(text, "Objective")
        participants = _parse_participants(_extract_section(text, "Participants"))
        evidence = _parse_review_evidence(_extract_section(text, "Review Evidence"))
        checkpoints = _extract_section(text, "Review Checkpoints").splitlines()
        result.append(
            {
                "wave_id": wave["wave_id"],
                "status": wave["status"],
                "title": title_match.group(1).strip() if title_match else wave["wave_id"],
                "objective": objective.splitlines()[0].strip() if objective else "",
                "path": str(wave_md.relative_to(root)).replace("\\", "/"),
                "change_count": len(wave.get("changes", [])),
                "changes": wave.get("changes", []),
                "participants": participants,
                "review_evidence": evidence,
                "review_checkpoint_preview": [line.strip() for line in checkpoints if line.strip()][:4],
                "last_updated": datetime.fromtimestamp(wave_md.stat().st_mtime, UTC).isoformat(),
            }
        )
    return result


def _iter_porcelain_z(raw: str):
    """Yield ``(xy, path)`` for each record in ``git status --porcelain -z`` output.

    In ``-z`` mode paths are emitted raw and unquoted (no C-octal escaping, no
    surrounding quotes), so non-ASCII / spaced names resolve on disk directly.
    A rename/copy entry emits the destination path in the ``XY`` record followed
    by a separate NUL-terminated origin-path token; the origin token is consumed
    here (not yielded), matching the prior behaviour of reporting the new path.
    """
    tokens = raw.split("\0")
    i, n = 0, len(tokens)
    while i < n:
        tok = tokens[i]
        i += 1
        if len(tok) < 4:  # empty trailing token, or malformed record
            continue
        xy, path = tok[:2], tok[3:]
        if ("R" in xy or "C" in xy) and i < n:
            i += 1  # consume the rename/copy origin-path token
        yield xy, path


def list_git_changed_files(root: Path, since: date | None = None, limit: int = 500) -> list[dict[str, str]]:
    """Return changed files as {path, status} dicts.

    When ``since`` is set, combines:
    - Committed changes on or after ``since`` (git log)
    - Uncommitted changes with mtime >= ``since`` (git status)
    Uncommitted status takes precedence for files appearing in both.
    When ``since`` is None, returns all uncommitted files (git status only).
    """
    def run(*args: str) -> str:
        try:
            r = subprocess_util.isolated_run(
                ["git", *args], cwd=root, capture_output=True, text=True, timeout=10
            )
            return r.stdout if r.returncode == 0 else ""
        except Exception:
            return ""

    # Collect uncommitted files from git status
    seen: dict[str, str] = {}  # path → status, uncommitted takes precedence
    for xy, rel in _iter_porcelain_z(run("status", "--porcelain", "--untracked-files=all", "-z")):
        # --untracked-files=all expands fully-untracked dirs into individual files;
        # -z gives raw, unquoted paths. The trailing-slash skip remains a harmless
        # guard for entries git still reports as dirs (e.g. nested worktrees).
        if not rel or rel.endswith("/"):
            continue
        if "D" in xy:
            status = "deleted"
        elif xy == "??" or "A" in xy:
            status = "added"
        else:
            status = "modified"
        if since is not None:
            if status == "deleted":
                continue
            try:
                cutoff = datetime(since.year, since.month, since.day).astimezone().timestamp()
                if (root / rel).stat().st_mtime < cutoff:
                    continue
            except OSError:
                continue
        seen[rel] = status

    # When filtering by date, also include files touched in commits since ``since``
    if since is not None:
        since_str = since.strftime("%Y-%m-%d")
        log_out = run("log", f"--since={since_str} 00:00:00", "--name-only", "--pretty=format:", "--diff-filter=ACDMR")
        for line in log_out.splitlines():
            rel = line.strip()
            if rel and not rel.endswith("/") and rel not in seen:
                seen[rel] = "modified"

    # Build line-count map from numstat (covers tracked modified/deleted files)
    numstat_map: dict[str, tuple[int | None, int | None]] = {}
    for numstat_args in (["diff", "--numstat", "HEAD"], ["diff", "--numstat", "--cached"]):
        for line in run(*numstat_args).splitlines():
            parts = line.split("\t", 2)
            if len(parts) != 3:
                continue
            added_s, deleted_s, rel_path = parts
            rel_path = rel_path.strip()
            try:
                a = int(added_s)
            except ValueError:
                a = None
            try:
                d = int(deleted_s)
            except ValueError:
                d = None
            existing = numstat_map.get(rel_path, (None, None))
            numstat_map[rel_path] = (
                (existing[0] or 0) + (a or 0) if (existing[0] is not None or a is not None) else None,
                (existing[1] or 0) + (d or 0) if (existing[1] is not None or d is not None) else None,
            )

    result = []
    for p, s in seen.items():
        la, ld = numstat_map.get(p, (None, None))
        # Untracked new files don't appear in numstat — count lines directly
        if la is None and s == "added":
            try:
                la = (root / p).read_text(encoding="utf-8", errors="replace").count("\n")
            except OSError:
                pass
        entry: dict[str, object] = {"path": p, "status": s}
        if la is not None:
            entry["lines_added"] = la
        if ld is not None:
            entry["lines_deleted"] = ld
        result.append(entry)
    return result[:limit]


def get_file_diff(root: Path, rel_path: str) -> tuple[str, int]:
    """Return (diff_text, http_status) for rel_path within root.

    Returns 400 for path traversal attempts. Untracked files are rendered
    as synthetic full-addition diffs. All other files use git diff HEAD.
    """
    try:
        resolved = (root / rel_path).resolve()
        resolved.relative_to(root.resolve())
    except (ValueError, OSError):
        return ("", 400)

    def _run(*args: str) -> str:
        try:
            r = subprocess_util.isolated_run(
                list(args), cwd=root, capture_output=True, text=True, timeout=10
            )
            return r.stdout
        except Exception:
            return ""

    status_out = _run("git", "status", "--porcelain", "--", rel_path)
    is_untracked = any(line.startswith("??") for line in status_out.splitlines())

    if is_untracked:
        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ("", 200)
        lines = content.splitlines()
        n = len(lines)
        header = f"--- /dev/null\n+++ b/{rel_path}\n@@ -0,0 +1,{n} @@\n"
        body = "".join(f"+{line}\n" for line in lines)
        return (header + body, 200)

    return (_run("git", "diff", "HEAD", "--", rel_path), 200)


def collect_activity(root: Path, change_sets: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    handoff_path = root / "docs" / "agents" / "session-handoff.md"
    handoff_text = handoff_path.read_text(encoding="utf-8") if handoff_path.exists() else ""
    active_match = _ACTIVE_WAVE_RE.search(handoff_text)
    recent_progress: list[dict[str, Any]] = []
    for item in change_sets["wave"] + change_sets["plan"]:
        for entry in item.get("progress_log", []):
            recent_progress.append(
                {
                    "change_id": item["change_id"],
                    "wave_id": item.get("wave_id") or "",
                    "path": item.get("path") or "",
                    "title": item["title"],
                    "scope": item["scope"],
                    "date": entry.get("date", ""),
                    "update": entry.get("update", ""),
                    "evidence": entry.get("evidence", ""),
                }
            )
    recent_progress.sort(key=lambda row: row.get("date", ""), reverse=True)
    return {
        "session_handoff_path": "docs/agents/session-handoff.md",
        "session_handoff_active_wave": active_match.group(1).strip() if active_match else "",
        "recent_progress": recent_progress[:10],
        "files_changed_all": list_git_changed_files(root),
    }


def _index_stats(meta: Any, build_stats: Any, index_dir: "Path | None" = None) -> dict[str, Any]:
    """Merge meta.json + index-build-stats.json into a flat stats dict.

    Files and chunk counts are read from the actual chunk data when index_dir is
    provided. The pack now ships Lance tables directly (`docs.lance` / `code.lance`),
    so the dashboard no longer reads legacy `docs.json` / `code.json` chunks.
    """
    m = meta if isinstance(meta, dict) else {}
    s = build_stats if isinstance(build_stats, dict) else {}
    model_versions = m.get("model_versions") or {}

    doc_chunks = 0
    code_chunks = 0
    files: set[str] = set()
    if index_dir is not None:
        lance_doc_chunks, lance_code_chunks, lance_files = _lance_table_stats(index_dir)
        doc_chunks = lance_doc_chunks
        code_chunks = lance_code_chunks
        files.update(lance_files)
    files_indexed = len(files) or int(s.get("files_indexed", 0) or len(m.get("file_meta") or {}) or (doc_chunks + code_chunks))
    if not doc_chunks:
        doc_chunks = int(s.get("doc_chunks", 0))
    if not code_chunks:
        code_chunks = int(s.get("code_chunks", 0))

    docs_model = str(model_versions.get("docs", "") or "")
    code_model = str(model_versions.get("code", "") or "")
    return {
        "present": bool(m),
        "built_at": m.get("built_at", "") or s.get("built_at", ""),
        "files_indexed": files_indexed,
        "doc_chunks": doc_chunks,
        "code_chunks": code_chunks,
        "elapsed_seconds": int(s.get("elapsed_seconds") or 0),
        "mode": str(s.get("mode", "")),
        "model": docs_model or code_model,
        "docs_model": docs_model,
        "code_model": code_model,
    }


def collect_health(root: Path, wave_count: int, change_sets: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    # Wave 1p4ww: single project index — the framework layer is folded in.
    index_dir        = root / ".wavefoundry" / "index"
    index_meta       = _read_json(index_dir    / "meta.json", {})
    index_stats      = _read_json(index_dir    / "index-build-stats.json", {})
    project_graph    = read_graph_payload(root, "project")
    project_build    = server.wave_index_build_status_response(root, layer="project").get("data", {})
    project_health   = _index_stats(index_meta,    index_stats,    index_dir)
    if isinstance(project_build, dict):
        project_state = str(project_build.get("build_status") or project_build.get("state") or "").strip().lower()
        if project_state in {"running", "failed"}:
            if "state" in project_build and "build_status" not in project_build:
                project_build = {**project_build, "build_status": project_build.get("state")}
            project_health.update(project_build)
        elif project_build.get("stale_locks_cleaned"):
            project_health["stale_locks_cleaned"] = project_build["stale_locks_cleaned"]
    return {
        "docs_lint": {"status": "unknown", "reason": "Run on demand outside the dashboard poll loop."},
        "index": {
            "project": project_health,
        },
        "graph": {
            "project": project_graph,
        },
        "counts": {
            "waves": wave_count,
            "wave_changes": len(change_sets["wave"]),
            "planned_changes": len(change_sets["plan"]),
        },
    }


_AGENT_ROLE_RE   = re.compile(r"^Role:\s+(.+)$", re.MULTILINE)
_AGENT_CATEGORY_RE = re.compile(r"^Category:\s+(.+)$", re.MULTILINE)

_HEADER_STRIP_PREFIXES = (
    "Owner:", "Status:", "Category:", "Last verified:", "Role:", "Actor:",
    "Schema version:", "Last distilled:",
)


def _strip_agent_header(text: str) -> str:
    """Strip the metadata header block from an agent doc, returning the body.

    Tolerates blank lines within the header block (common in journal files).
    Stops at the first non-blank line that does not match a known metadata prefix.
    """
    lines = text.splitlines()
    i = 0
    if lines and lines[i].startswith("# "):
        i += 1
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        if any(stripped.startswith(p) for p in _HEADER_STRIP_PREFIXES):
            i += 1
            continue
        break
    return "\n".join(lines[i:]).strip()


_REVIEW_SUFFIXES = ("-reviewer", "-auditor", "-tester")
_REVIEW_STEMS = frozenset({"reality-checker"})
_COORDINATE_STEMS = frozenset({"guru", "planner", "wave-coordinator", "wave-council", "platform-mapping", "session-handoff"})
_COORDINATE_SUFFIXES = ("-coordinator", "-moderator")
_FACTOR_PREFIX = "factor-"
# Pattern-based: any stem ending with these suffixes is a hands-on builder.
# Exact matches cover framework agents whose stems don't end in a build suffix.
_BUILD_SUFFIXES = ("-engineer", "-developer", "-builder", "-automator", "-programmer", "-coder")
_BUILD_STEMS = frozenset({"implementer"})


def _classify_agent_category(stem: str, group: str) -> str:
    """Map an agent file stem + group to a functional display category."""
    if stem.startswith(_FACTOR_PREFIX):
        return "factor"
    if group == "persona":
        return "persona"
    if group == "journal":
        return "journal"
    if group == "factor":
        return "factor"
    if group == "specialist":
        return "specialist"
    if stem in _REVIEW_STEMS or any(stem.endswith(s) for s in _REVIEW_SUFFIXES):
        return "review"
    if stem in _COORDINATE_STEMS or any(stem.endswith(s) for s in _COORDINATE_SUFFIXES):
        return "coordinate"
    if stem in _BUILD_STEMS or any(stem.endswith(s) for s in _BUILD_SUFFIXES):
        return "build"
    return "specialist"


def _build_participant_usage_map(waves: list[dict[str, Any]]) -> dict[str, int]:
    """Count wave participations per role name (file-stem key: lowercase, hyphenated)."""
    counts: dict[str, int] = {}
    for wave in waves:
        seen_in_wave: set[str] = set()
        for pt in wave.get("participants", []):
            role = re.sub(r"\s+", "-", pt.get("role", "").strip().lower())
            if role and role not in seen_in_wave:
                counts[role] = counts.get(role, 0) + 1
                seen_in_wave.add(role)
    return counts


def _collect_agents_from_dir(
    agents_dir: Path, group: str, usage_map: dict[str, int] | None = None
) -> list[dict[str, Any]]:
    results = []
    for path in sorted(agents_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        if group == "agent" and path.stem.startswith(_FACTOR_PREFIX):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        role_m = _AGENT_ROLE_RE.search(text)
        if not role_m:
            continue  # No Role: field — not an agent role doc
        category_m = _AGENT_CATEGORY_RE.search(text)
        title_m = _TITLE_RE.search(text)
        title = title_m.group(1).strip() if title_m else path.stem.replace("-", " ").title()
        for prefix in ("Persona — ", "Persona: ", "Journal — ", "Specialist — "):
            if title.startswith(prefix):
                title = title[len(prefix):]
                break
        usage = (usage_map or {}).get(path.stem, 0)
        results.append({
            "name": title,
            "group": group,
            "category": category_m.group(1).strip() if category_m else _classify_agent_category(path.stem, group),
            "role": role_m.group(1).strip(),
            "usage_count": usage,
            "path": str(path.relative_to(path.parent.parent.parent)).replace("\\", "/"),
            "body": _strip_agent_header(text),
        })
    return results


def _collect_factor_agents(root: Path, usage_map: dict[str, int] | None = None) -> list[dict[str, Any]]:
    """Collect factor-review agents from canonical docs, falling back to wrappers."""
    factors_dirs = []
    docs_factor_dir = root / "docs" / "agents"
    if docs_factor_dir.is_dir():
        factors_dirs.append(docs_factor_dir)
    legacy_factor_dir = root / ".claude" / "agents"
    if not factors_dirs and legacy_factor_dir.is_dir():
        factors_dirs.append(legacy_factor_dir)
    results: list[dict[str, Any]] = []
    for factors_dir in factors_dirs:
        for path in sorted(factors_dir.glob("factor-*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            category_m = _AGENT_CATEGORY_RE.search(text)
            title_m = _TITLE_RE.search(text)
            title = title_m.group(1).strip() if title_m else path.stem.replace("-", " ").title()
            if title.startswith("Factor ") and " — " in title:
                title = title.split(" — ", 1)[1].strip() or title
            usage = (usage_map or {}).get(path.stem, 0)
            results.append({
                "name": title,
                "group": "factor",
                "category": category_m.group(1).strip() if category_m else _classify_agent_category(path.stem, "factor"),
                "role": path.stem,
                "usage_count": usage,
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "body": _strip_agent_header(text),
            })
    return results


def collect_agents(root: Path, usage_map: dict[str, int] | None = None) -> list[dict[str, Any]]:
    agents_root = root / "docs" / "agents"
    if not agents_root.is_dir():
        return []
    agents: list[dict[str, Any]] = []
    agents.extend(_collect_agents_from_dir(agents_root, "agent", usage_map))
    for sub, group in [("personas", "persona"), ("specialists", "specialist")]:
        subdir = agents_root / sub
        if subdir.is_dir():
            agents.extend(_collect_agents_from_dir(subdir, group, usage_map))
    agents.extend(_collect_factor_agents(root, usage_map))
    agents.sort(key=lambda a: a["name"])
    return agents


def collect_git_stats(root: Path) -> dict[str, Any]:
    """Collect local git statistics for the dashboard hero area."""
    def run(*args: str) -> str:
        try:
            r = subprocess_util.isolated_run(
                ["git", *args], cwd=root, capture_output=True, text=True, timeout=5
            )
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""

    def run_raw(*args: str) -> str:
        # NUL-delimited (-z) output must NOT be stripped: leading whitespace is
        # significant — an unstaged-change record begins with a space in its XY code
        # (" M path"), and a filename may itself begin/end with whitespace. Stripping
        # the whole blob corrupts the first/last token (and can drop a short first
        # record below the 4-char floor). Mirror list_git_changed_files's raw read.
        try:
            r = subprocess_util.isolated_run(
                ["git", *args], cwd=root, capture_output=True, text=True, timeout=5
            )
            return r.stdout if r.returncode == 0 else ""
        except Exception:
            return ""

    branch = run("rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":
        branch = run("rev-parse", "--short", "HEAD")

    commit_hash = run("rev-parse", "--short", "HEAD")
    commit_msg  = run("log", "-1", "--format=%s")
    commit_date = run("log", "-1", "--format=%cd", "--date=short")

    # File count: all modified/deleted/untracked files, enumerated individually.
    # --untracked-files=all expands fully-untracked dirs (default porcelain collapses
    # them to one "?? dir/" line) and -z gives raw paths + structural rename handling,
    # matching list_git_changed_files so the tile count equals the dialog list length
    # (below the dialog's 500-row cap).
    status_out = run_raw("status", "--porcelain", "--untracked-files=all", "-z")
    files_changed = sum(
        1 for _xy, rel in _iter_porcelain_z(status_out) if rel and not rel.endswith("/")
    )

    # Line stats: tracked file changes vs HEAD (staged + unstaged)
    shortstat = run("diff", "HEAD", "--shortstat")
    lines_added = lines_removed = 0
    if shortstat:
        if m := re.search(r"(\d+) insertion", shortstat):
            lines_added = int(m.group(1))
        if m := re.search(r"(\d+) deletion", shortstat):
            lines_removed = int(m.group(1))

    # Add lines from untracked files (git diff HEAD omits these entirely).
    # -z yields raw, unquoted, NUL-delimited paths so non-ASCII / spaced names
    # resolve on disk (a bare line-based listing would octal-escape them).
    untracked = run_raw("ls-files", "--others", "--exclude-standard", "-z")
    for rel in (untracked.split("\0") if untracked else []):
        if not rel or rel.endswith("/"):  # skip directory entries (e.g. nested worktrees)
            continue
        try:
            data = (root / rel).read_bytes()
            if b"\x00" in data:  # binary file — skip to avoid garbage line counts
                continue
            lines_added += data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
        except OSError:
            pass

    ahead = behind = 0
    upstream = run("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if upstream:
        ab = run("rev-list", "--count", "--left-right", f"{upstream}...HEAD")
        if "\t" in ab:
            b, a = ab.split("\t", 1)
            behind = int(b) if b.isdigit() else 0
            ahead  = int(a) if a.isdigit() else 0

    return {
        "branch": branch,
        "commit_hash": commit_hash,
        "commit_message": (commit_msg[:72] + "…") if len(commit_msg) > 72 else commit_msg,
        "commit_date": commit_date,
        "files_changed": files_changed,
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "ahead": ahead,
        "behind": behind,
    }


def collect_dashboard_snapshot(root: Path, skip_git: bool = False) -> dict[str, Any]:
    config = read_dashboard_config(root)
    waves = collect_waves(root)
    change_sets = collect_changes(root)
    current = server.current_wave(root)
    manifest = read_prompt_manifest(root)
    project_name = derive_project_name(root)
    change_lookup = {c["change_id"]: c for c in change_sets["wave"]}
    metrics = _wave_only_metric_counts(
        waves,
        change_sets["wave"],
        change_sets["plan"],
        current.get("wave_id") if isinstance(current, dict) else None,
    )
    for wave in waves:
        wave["changes"] = [
            {
                "id": c["id"],
                "status": c.get("status", "unknown"),
                "title": change_lookup.get(c["id"], {}).get("title", c["id"]),
                "description": change_lookup.get(c["id"], {}).get("description", ""),
                "kind": change_lookup.get(c["id"], {}).get("kind", "change"),
            }
            for c in wave.get("changes", [])
        ]
    wave_status_counts: dict[str, int] = {}
    for wave in waves:
        status = str(wave["status"]).lower()
        wave_status_counts[status] = wave_status_counts.get(status, 0) + 1
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "config": {
            "poll_interval_ms": config["poll_interval_ms"],
            "entrypoint": config["entrypoint"],
            "terminology": config["terminology"],
        },
        "project": {
            "name": project_name,
            "repo_root": str(root),
            "repo_basename": root.name,
            "readme_title": read_readme_title(root),
            "framework_revision": str(manifest.get("framework_revision", "")),
            "framework_version": read_framework_version(root),
            "project_archetypes": read_repo_profile(root).get("project_archetypes", []),
            "active_wave_id": current.get("wave_id") if isinstance(current, dict) else None,
            "wave_status_counts": wave_status_counts,
            "public_prompt_count": len(manifest.get("public_prompt_surface", [])) if isinstance(manifest.get("public_prompt_surface"), list) else 0,
        },
        "waves": waves,
        "changes": {
            "in_waves": change_sets["wave"],
            "staged": change_sets["plan"],
        },
        "metrics": {
            "waves": {
                "active": len([wave for wave in waves if wave["status"] == "active"]),
                "pending": len([wave for wave in waves if wave["status"] != "active" and wave["status"] != "closed" and wave["status"] != "completed"]),
                "total": len(waves),
            },
            **metrics,
        },
        "activity": collect_activity(root, change_sets),
        "health": collect_health(root, len(waves), change_sets),
        "agents": collect_agents(root, _build_participant_usage_map(waves)),
        "git": {} if skip_git else collect_git_stats(root),
    }

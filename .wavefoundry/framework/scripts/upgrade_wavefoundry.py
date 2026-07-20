#!/usr/bin/env python3
"""Automated Wavefoundry upgrade script.

Handles the mechanical phases of a framework upgrade so the agent retains
ownership of high-judgment editing work (drift detection, journal
reconciliation, spec gap remediation).

Usage:
    python3 .wavefoundry/framework/scripts/upgrade_wavefoundry.py [options]

Phases (run in order when no phase flag given):
    Phase 0 — Pre-flight: dashboard check, version guard, MANIFEST backup,
              zip detection, change plan, confirmation prompt, lock file write.
    Phase 1 — Surface rendering: render_platform_surfaces.py
    Phase 2 — Pruning: prune_framework.py --old-manifest <saved MANIFEST>
    Phase 3 — Docs gate: docs-gardener && docs-lint

Separate phase (called after agent editing pass):
    Phase 4 — Index update: setup_index.py (docs, incremental — auto-escalates to
              full rebuild only when chunker/model version changed) then
              setup_index.py --background-code (code, background)

Phase 5 — Cleanup (called after phase 4, or via --cleanup):
    Remove upgrade lock; print operator summary.

Exit codes:
    0 — success
    1 — docs gate failed
    2 — surface rendering failed
    3 — pre-flight check failed (downgrade detected, lock already present, etc.)
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import zipfile
from pathlib import Path

# ── Resolve paths ─────────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent
FRAMEWORK_DIR = SCRIPTS_DIR.parent
BIN_DIR = FRAMEWORK_DIR / "bin"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)
import subprocess_util  # shared subprocess isolation (wave 1p8gu)
import cli_stdio  # shared UTF-8 stdio reconfigure (wave 1p8gv)

# Wave 1p8gv: a native-Windows upgrade crashed printing `⚠` because nothing reconfigured stdout to
# UTF-8. Reconfigure at import so EVERY entry into this module (CLI, `wf upgrade`, MCP `wf_upgrade`
# which re-execs this script) prints non-ASCII without raising on a cp1252 console.
cli_stdio.configure_utf8_stdio()

# Wave 1p8gv: `/tmp` does not exist on native Windows — the old fallback raised FileNotFoundError when
# copying the pre-upgrade MANIFEST. `tempfile.gettempdir()` resolves the correct OS temp dir (honors
# TMPDIR/TEMP/TMP) cross-platform.
OLD_MANIFEST_TMP = Path(tempfile.gettempdir()) / "wf-manifest-old.txt"

UPGRADE_LOG_FILENAME = "upgrade.log"

# Wave 1p8eu: the operator summary is built ONCE as a dict and emitted machine-readably on a single
# line prefixed with this sentinel (alongside the human prose). ``server_impl.wf_upgrade_response``
# parses the line back into ``data['summary']`` (fail-safe: an absent/malformed line falls back to the
# raw ``output``). Keep this string stable — it is the parse contract between the two modules.
WAVE_UPGRADE_SUMMARY_SENTINEL = "WAVE_UPGRADE_SUMMARY_JSON:"

# Wave 1p5do: the lowest installed version this pack still carries migrations for. Migrations for
# transitions older than 1.4→1.5 have been pruned, so upgrading from below this floor may silently
# skip an intermediate migration. Enforced as a loud WARNING (not an abort): all known projects are
# ≥ 1.5.1, so nothing is actually below it — the floor makes the published 1.5.0 "floor is 1.4.0"
# claim real and self-documents the supported range without blocking a legitimate edge case.
SUPPORTED_UPGRADE_FLOOR = "1.4.0"


def upgrade_log_path(root: Path) -> Path:
    return root / ".wavefoundry" / "logs" / UPGRADE_LOG_FILENAME


def _tool_venv_base() -> Path:
    """Tool-venv base path — delegates to the single resolver (wave 1p7pl)."""
    return venv_bootstrap.tool_venv_base()


def _preferred_python() -> str:
    """Return the spawn interpreter: tool-venv ``pythonw.exe`` on Windows, else tool-venv Python.

    Builds the venv path via the single resolver (wave 1p7pl). On native Windows, prefers the
    console-free tool-venv ``pythonw.exe`` when present so spawned framework processes never flash a
    console window (wave 1p8pe). Every consumer of this resolver is non-interactive and redirects its
    output. POSIX is unchanged (``windowless_pythonw()`` returns ``None``).
    """
    pythonw = subprocess_util.windowless_pythonw()
    if pythonw is not None:
        return pythonw
    vp = venv_bootstrap.tool_venv_python()
    return str(vp) if vp.exists() else sys.executable


# ── Log file tee ──────────────────────────────────────────────────────────────
# All _log() / _err() output goes to stdout AND to the upgrade log file so
# operators can `tail -f .wavefoundry/logs/upgrade.log` for real-time progress.

import io as _io

_log_file: "_io.TextIOWrapper | None" = None


def _open_log(root: Path, mode: str = "w") -> None:
    """Open (or reopen) the upgrade log file.

    ``mode="w"`` truncates for a fresh upgrade run (phases 0–3).
    ``mode="a"`` appends for continuation phases (--update-index, --cleanup).
    """
    global _log_file
    _close_log()
    log_path = upgrade_log_path(root)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _log_file = log_path.open(mode, encoding="utf-8", buffering=1)  # line-buffered
    except OSError as exc:
        print(f"  ⚠  Could not open upgrade log {log_path}: {exc}", flush=True)


def _close_log() -> None:
    global _log_file
    if _log_file is not None:
        try:
            _log_file.close()
        except OSError:
            pass
        _log_file = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _log(msg: str) -> None:
    print(msg, flush=True)
    if _log_file is not None:
        try:
            ts = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
            _log_file.write(f"{ts} {msg}\n")
        except OSError:
            pass


def _err(msg: str) -> None:
    full = f"ERROR: {msg}"
    print(full, file=sys.stderr, flush=True)
    if _log_file is not None:
        try:
            ts = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
            _log_file.write(f"{ts} {full}\n")
        except OSError:
            pass


def _detect_dashboard(root: Path) -> tuple[bool, int | None, str | None]:
    """Return (running, pid, url) for the local dashboard."""
    # Upgrade-only compatibility probe: recognize the canonical carrier first
    # and the pre-cutover root carrier second so the one-way migration can stop
    # an old dashboard before installing canonical-only runtime code.
    candidates = (
        root / ".wavefoundry" / "locks" / "dashboard-server.lock",
        root / ".wavefoundry" / "dashboard-server.lock",
    )
    meta = next((path for path in candidates if path.exists()), None)
    if meta is None:
        return False, None, None
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
        pid = data.get("pid")
        url = data.get("url")
        if isinstance(pid, int) and pid > 0:
            # Wave 1p654 (review follow-up): harden the liveness check to match the
            # lifecycle tools — a bare os.kill(pid, 0) accepts a zombie or a recycled
            # PID. Verify the recorded PID is actually a live dashboard for THIS root
            # via the shared cmdline scan; fall back to the pid-liveness helper when the
            # scan is unavailable (Windows / ps error).
            try:
                import dashboard_lib
                live = dashboard_lib.dashboard_cmdline_pids(root)
            except Exception:  # noqa: BLE001 — best-effort; fall back to _pid_is_running
                live = None
            if live is not None and pid not in live:
                return False, None, None
            # Wave 1p9hi: use the cross-OS liveness helper, NOT a bare os.kill(pid, 0). On Windows
            # os.kill(pid, 0) routes to GenerateConsoleCtrlEvent/TerminateProcess (signal 0 ==
            # signal.CTRL_C_EVENT), not a benign probe: it can raise OSError (mis-reporting a live
            # dashboard as absent → the upgrade never pauses it) or fire a spurious Ctrl+C event.
            # This is the last unmigrated liveness site — the three siblings (upgrade_lib,
            # indexer, server_impl) already branch on os.name. _pid_is_running uses tasklist on
            # Windows; on POSIX it is the same os.kill(pid, 0) probe, so POSIX behavior is unchanged.
            import upgrade_lib
            if upgrade_lib._pid_is_running(pid):
                return True, pid, url
    except (OSError, json.JSONDecodeError):
        pass
    return False, None, None


import re as _re

_ZIP_NAME_RE = _re.compile(r"^wavefoundry-(\d+\.\d+\.\d+)\.([A-Za-z0-9]+)\.zip$")
_HOME_DIR = Path("~")
_HOME_WAVEFOUNDRY_DIR = Path("~/.wavefoundry")
_DIST_DIR = Path("~/.wavefoundry/dist")
_DOWNLOADS_DIR = Path("~/Downloads")  # 1p5dk: browser-downloaded packs commonly land here


# 1p8xl: pack-search locations that could not be read (e.g. a macOS-TCC-sandboxed ``~/Downloads``).
# A permission/sandbox error on ONE location must never abort the upgrade — it is logged, skipped, and
# recorded here so the upgrade summary can surface it for operator acknowledgment.
_PACK_SCAN_SKIPPED: list[str] = []


def _record_skipped_scan_location(search_dir: Path, exc: OSError) -> None:
    """Log + record a pack-search location that could not be scanned (permission/sandbox)."""
    loc = str(search_dir)
    if loc not in _PACK_SCAN_SKIPPED:
        _PACK_SCAN_SKIPPED.append(loc)
    _log(
        f"⚠  Could not scan {loc} for packs ({type(exc).__name__}); skipping that location. "
        "If a newer pack lives there, grant the host access to it and re-run."
    )


def _scan_dir_entries(search_dir: Path) -> "list | None":
    """Return the directory listing, or ``None`` when the location is absent or unreadable.

    A non-directory is skipped silently (``None``); a permission/sandbox ``OSError`` (e.g. macOS TCC
    on ``~/Downloads``) is logged + recorded via ``_record_skipped_scan_location`` and skipped — it
    never propagates, so one inaccessible location cannot abort pack discovery (1p8xl)."""
    try:
        if not search_dir.is_dir():
            return None
        return list(search_dir.iterdir())
    except OSError as exc:
        _record_skipped_scan_location(search_dir, exc)
        return None


def _find_latest_release_zip(root: Path) -> Path | None:
    """Return the highest-semver wavefoundry zip across the supported search paths.

    Search locations:
      1. repository root
      2. ~/
      3. ~/.wavefoundry/
      4. ~/.wavefoundry/dist/
      5. ~/Downloads/

    Non-matching filenames are skipped silently. When multiple zips share the
    same MAJOR.MINOR.PATCH, the file with the most recent mtime is returned
    (wave 131bt 131ht). Lexicographic build-suffix comparison is the deterministic
    fallback when mtimes tie exactly, so the selection is stable across reruns.

    Background: 1.3.4+ build suffixes are temporally lex-monotonic by construction
    (wave 131bt 131bu integer-packed encoding), so semver+suffix would also give
    the right answer for those builds. Mtime is preferred regardless because it
    handles same-bucket builds (5-minute collision window) and any future scheme
    change correctly without the selector having to track build-encoding versions.
    """
    try:
        from check_version import _to_version
    except (ImportError, ModuleNotFoundError):
        return None
    best: tuple | None = None
    best_path: Path | None = None
    search_dirs = (
        root,
        _HOME_DIR.expanduser(),
        _HOME_WAVEFOUNDRY_DIR.expanduser(),
        _DIST_DIR.expanduser(),
        _DOWNLOADS_DIR.expanduser(),
    )
    _PACK_SCAN_SKIPPED.clear()
    for search_dir in search_dirs:
        entries = _scan_dir_entries(search_dir)
        if entries is None:
            continue
        for entry in entries:
            m = _ZIP_NAME_RE.match(entry.name)
            if not m:
                continue
            ver_str, build = m.group(1), m.group(2)
            try:
                v = _to_version(ver_str)
            except (ValueError, Exception):
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                mtime = 0.0
            # Tuple comparison: semver primary, then mtime, then build string for determinism.
            key = (v, mtime, build)
            if best is None or key > best:
                best = key
                best_path = entry
    return best_path


def _find_zip(root: Path) -> Path | None:
    """Return the best available wavefoundry zip, or None.

    Search order:
      1. highest semver zip across repo root, ~/, ~/.wavefoundry/, ~/.wavefoundry/dist/, and ~/Downloads/
    """
    return _find_latest_release_zip(root)


def _print_all_release_zips(root: Path) -> None:
    """Print every matching wavefoundry zip across all search paths, semver-sorted.

    Highest version first. The selected-latest is prefixed with `* `. Format
    per line is `<marker> <version> <path>`. Output stays empty when no zips
    are found (callers can grep / wc on it without special-casing).

    Used by `upgrade_wavefoundry.py --list-zips` to give agents an
    authoritative inventory instead of having them shell out to `ls -1`
    (which sorts lexicographically and ranks `1.3.9` above `1.3.30`).
    """
    try:
        from check_version import _to_version
    except (ImportError, ModuleNotFoundError):
        return
    seen: dict[Path, tuple] = {}
    search_dirs = (
        root,
        _HOME_DIR.expanduser(),
        _HOME_WAVEFOUNDRY_DIR.expanduser(),
        _DIST_DIR.expanduser(),
        _DOWNLOADS_DIR.expanduser(),
    )
    for search_dir in search_dirs:
        entries = _scan_dir_entries(search_dir)
        if entries is None:
            continue
        for entry in entries:
            m = _ZIP_NAME_RE.match(entry.name)
            if not m:
                continue
            ver_str, build = m.group(1), m.group(2)
            try:
                v = _to_version(ver_str)
            except (ValueError, Exception):
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                mtime = 0.0
            # Dedupe by resolved absolute path so symlinked dirs don't
            # emit duplicate entries.
            seen[entry.resolve()] = (v, mtime, build, ver_str)
    if not seen:
        return
    # Sort highest-first by (semver, mtime, build).
    ordered = sorted(seen.items(), key=lambda kv: kv[1], reverse=True)
    selected = ordered[0][0] if ordered else None
    for path, (_v, _mtime, _build, ver_str) in ordered:
        marker = "*" if path == selected else " "
        print(f"{marker} {ver_str} {path}")


def _read_pack_version(root: Path) -> str | None:
    p = root / ".wavefoundry" / "framework" / "VERSION"
    try:
        return p.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _tree_already_at(root: Path, to_version: str | None) -> bool:
    """Wave 1p44r — True when the on-disk framework already equals *to_version*, so
    re-extracting the pack would be a redundant (and destructive) no-op. False for
    an unknown/None target so a genuine upgrade is never skipped."""
    if to_version in (None, "unknown"):
        return False
    return _read_pack_version(root) == to_version


def _read_installed_revision(root: Path) -> str | None:
    """Installed framework revision — delegates to the single canonical resolver in
    check_version (wave 1p44p), so there is exactly one place that resolves the
    installed revision (`framework_revision` from prompt-surface-manifest.json,
    falling back to framework/VERSION). The old MANIFEST `json.loads` path (which
    always raised → None, disabling the downgrade guard) is removed."""
    from check_version import _read_installed_revision as _resolve
    return _resolve(root)


def _stamp_manifest_revision(root: Path) -> bool:
    """Wave 1p44p follow-up — stamp the just-installed framework version into
    ``docs/prompts/prompt-surface-manifest.json``'s ``framework_revision`` after the
    tree is extracted and surfaces are rendered.

    The pack ships ``framework/VERSION`` but NOT the consumer's manifest, and only
    the self-host packager (``build_pack.update_manifest_revision``) ever wrote this
    field — so on a consumer upgrade ``VERSION`` advances while ``framework_revision``
    stays frozen at the pre-upgrade value, leaving the downgrade guard / seed-160
    step-3 version check reading a stale revision. Stamping here makes the field
    authoritative again and self-heals an already-stale consumer on its next upgrade.

    Read-modify-write preserves every other manifest key (matches build_pack's
    ``indent=2`` + trailing-newline format). No-op — returns False — when VERSION is
    unreadable or the manifest is absent/unparseable; never CREATES the manifest."""
    version = _read_pack_version(root)
    if not version:
        return False
    manifest = root / "docs" / "prompts" / "prompt-surface-manifest.json"
    if not manifest.is_file():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict) or data.get("framework_revision") == version:
        return False
    data["framework_revision"] = version
    try:
        manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except OSError:
        return False
    return True


def _read_zip_version(zip_path: Path) -> str | None:
    """Read VERSION from inside the zip without extracting."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            # VERSION lives at .wavefoundry/framework/VERSION inside the zip
            for candidate in (".wavefoundry/framework/VERSION", "framework/VERSION"):
                if candidate in names:
                    return zf.read(candidate).decode("utf-8").strip() or None
    except (OSError, zipfile.BadZipFile, KeyError):
        pass
    return None


def _detect_prompt_files(root: Path) -> list[str]:
    """Find docs/prompts/*.md files that lack .prompt.md extension (migration needed)."""
    prompts_dir = root / "docs" / "prompts"
    if not prompts_dir.is_dir():
        return []
    results = []
    for p in sorted(prompts_dir.rglob("*.md")):
        if p.name in ("index.md", "README.md"):
            continue
        if p.name.endswith(".prompt.md"):
            continue
        rel = p.relative_to(root)
        # Only maxdepth 2 from docs/prompts
        if len(rel.parts) <= 4:
            results.append(str(rel))
    return results


def _compute_seed_diffs(
    root: Path, zip_path: Path
) -> list[tuple[str, str, str]]:
    """Compare seeds inside *zip_path* to seeds currently on disk.

    Returns a list of ``(filename, status, unified_diff_text)`` tuples, one per
    changed seed, where *status* is ``"modified"``, ``"added"``, or
    ``"removed"``.  Unchanged seeds are omitted.  Never raises — errors reading
    individual entries are logged and skipped.
    """
    import difflib

    # Seeds live at one of two paths inside the zip depending on how it was built.
    SEED_PREFIXES = (
        ".wavefoundry/framework/seeds/",
        "framework/seeds/",
    )

    # ── Read seeds from disk ──────────────────────────────────────────────────
    disk_seeds: dict[str, str] = {}
    seeds_dir = root / ".wavefoundry" / "framework" / "seeds"
    if seeds_dir.is_dir():
        for f in sorted(seeds_dir.rglob("*.md")):
            rel = f.relative_to(seeds_dir).as_posix()
            try:
                disk_seeds[rel] = f.read_text(encoding="utf-8")
            except OSError as exc:
                _log(f"  ⚠  Could not read disk seed {rel}: {exc}")

    # ── Read seeds from zip ───────────────────────────────────────────────────
    zip_seeds: dict[str, str] = {}
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                for prefix in SEED_PREFIXES:
                    if name.startswith(prefix) and name.endswith(".md"):
                        rel = name[len(prefix):]
                        if not rel:  # directory entry
                            break
                        try:
                            zip_seeds[rel] = zf.read(name).decode("utf-8")
                        except Exception as exc:  # noqa: BLE001
                            _log(f"  ⚠  Could not read zip seed {rel}: {exc}")
                        break
    except (OSError, zipfile.BadZipFile) as exc:
        _log(f"  ⚠  Could not read seeds from zip: {exc}")
        return []

    # ── Diff ──────────────────────────────────────────────────────────────────
    results: list[tuple[str, str, str]] = []
    for filename in sorted(set(disk_seeds) | set(zip_seeds)):
        old_text = disk_seeds.get(filename, "")
        new_text = zip_seeds.get(filename, "")
        if old_text == new_text:
            continue
        if not old_text:
            status = "added"
            from_label, to_label = "/dev/null", f"b/{filename}"
        elif not new_text:
            status = "removed"
            from_label, to_label = f"a/{filename}", "/dev/null"
        else:
            status = "modified"
            from_label, to_label = f"a/{filename}", f"b/{filename}"
        diff_lines = list(difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=from_label,
            tofile=to_label,
        ))
        results.append((filename, status, "".join(diff_lines)))
    return results


# ── Framework version transition detection (1p3dk / 1p3ho) ──────────────────
#
# Operator-visible logging of any framework version constant change at upgrade
# time. The indexer's `build_index` auto-escalate handles chunker/walker
# mismatches via full rebuild. The graph layer is materialized DURING the upgrade
# by Phase 4b (`phase_index_update` runs `setup_index --graph-only` as a fresh
# subprocess): opening the per-file graph state store calls
# `GraphStateStore.ensure_current()`, which resets the store and forces a
# full-corpus re-extraction whenever the pack's `GRAPH_BUILDER_VERSION` differs
# from the persisted one — independent of `--full`. The in-process first-query
# rebuild (`graph_query._ensure_graph_builder_current`) is only a SAFETY NET for
# when Phase 4b is skipped; note it can DOWNGRADE the graph if an already-running
# MCP server holds the pre-upgrade extractor in memory (hence the mandatory
# post-upgrade `wf_reload_mcp`/restart — see the upgrade prompt). This module's
# job is to surface those transitions in the upgrade log so operators see what
# changed, then trust Phase 4b / the graph layer to do the right thing.

_VERSION_CONSTANT_RE_TEMPLATE = (
    r'^{name}\s*=\s*["\']([^"\']+)["\']'
)


def _read_version_constant(file_path: Path, constant_name: str) -> str:
    """Read a top-level `CONSTANT = "value"` declaration from a Python file
    via regex (no import — avoids stale sys.modules / cwd issues during
    upgrade). Returns empty string when file or constant is missing.
    """
    if not file_path.is_file():
        return ""
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    pattern = _re.compile(
        _VERSION_CONSTANT_RE_TEMPLATE.format(name=constant_name),
        _re.MULTILINE,
    )
    m = pattern.search(text)
    return m.group(1) if m else ""


def _read_index_build_meta(root: Path) -> dict:
    """1sed6 (review-hardened): build-state read is STORE-ONLY — a legacy
    ``meta.json`` is never read, not even for version comparison. An absent or
    empty store returns {} = UNKNOWN, and every caller treats unknown as
    stale/needs-convergence, so a pre-1sed6 consumer converges by
    reconstruction (empty layer state → one re-chunk pass with vector reuse)
    rather than letting stale JSON claims skip required work. Bounded read —
    summary scalars only, no per-file rows."""
    index_dir = root / ".wavefoundry" / "index"
    try:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            "index_state_store", SCRIPTS_DIR / "index_state_store.py"
        )
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        summary = _mod.read_build_summary(index_dir)
        return summary if isinstance(summary, dict) else {}
    except Exception:
        return {}


# Backwards-compatible name (1p3ho v1 callers; kept for the existing test surface).
def _snapshot_pre_extract_chunker_versions(root: Path) -> dict[str, str]:
    """Read the consumer's pre-existing per-layer ``chunker_versions`` from
    the index-state store (1sed6: store-only — a legacy meta.json is never
    read). Empty dict when the store is absent/unreadable = unknown, which
    every caller treats as needing convergence."""
    data = _read_index_build_meta(root)
    if not data:
        return {}
    versions = data.get("chunker_versions")
    if isinstance(versions, dict):
        return {k: str(v) for k, v in versions.items() if isinstance(v, (str, int))}
    legacy = data.get("chunker_version")
    if isinstance(legacy, (str, int)) and str(legacy).strip():
        return {"docs": str(legacy), "code": str(legacy)}
    return {}


def _read_chunker_version_from_pack(root: Path) -> str:
    """Read CHUNKER_VERSION from the extracted pack's chunker.py."""
    return _read_version_constant(
        root / ".wavefoundry" / "framework" / "scripts" / "chunker.py",
        "CHUNKER_VERSION",
    )


def _read_walker_version_from_pack(root: Path) -> str:
    """Read WALKER_VERSION from the extracted pack's indexer.py."""
    return _read_version_constant(
        root / ".wavefoundry" / "framework" / "scripts" / "indexer.py",
        "WALKER_VERSION",
    )


def _read_graph_builder_version_from_pack(root: Path) -> str:
    """Read GRAPH_BUILDER_VERSION from the extracted pack's graph_indexer.py."""
    return _read_version_constant(
        root / ".wavefoundry" / "framework" / "scripts" / "graph_indexer.py",
        "GRAPH_BUILDER_VERSION",
    )


def _read_installed_graph_builder_version(root: Path) -> str:
    """Read the INSTALLED (pre-extract) project graph builder version from the real project graph state.

    Wave 1rvfx: the state lives under ``.wavefoundry/index/graph/`` — the SQLite store
    ``project-graph-state.sqlite`` (``meta`` table, ``key='builder_version'``) with a fallback to the
    legacy monolithic ``project-graph-state.json`` (``builder_version`` key). Mirrors the canonical
    ``graph_indexer.read_state_builder_version`` but is inlined with stdlib ``sqlite3``/``json`` only —
    the upgrade module deliberately avoids importing the heavy, tree-sitter-dependent ``graph_indexer``
    (which is also replaced during extraction). Read-only URI open (no file creation, sub-ms). Returns
    ``""`` when the state is absent/unreadable — FAIL-SAFE: the upgrade must never abort because this
    operator-log version probe could not read state (matches read_state_builder_version's contract).
    (The retired framework-graph layer's ``framework-graph-state.json`` is intentionally NOT read — it
    never exists in a current install, which is why the transition log line used to never fire.)"""
    import sqlite3  # local import — stdlib-only, keeps the upgrade module import-light
    graph_dir = root / ".wavefoundry" / "index" / "graph"
    store_path = graph_dir / "project-graph-state.sqlite"
    if store_path.exists():
        try:
            conn = sqlite3.connect(f"file:{store_path.as_posix()}?mode=ro", uri=True, timeout=2.0)
            try:
                row = conn.execute("SELECT value FROM meta WHERE key = 'builder_version'").fetchone()
            finally:
                conn.close()
            if row and row[0]:
                return str(row[0])
        except (sqlite3.Error, OSError):
            return ""
        return ""
    legacy_path = graph_dir / "project-graph-state.json"
    if legacy_path.is_file():
        try:
            data = json.loads(legacy_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                gb = data.get("builder_version")
                if isinstance(gb, (str, int)) and str(gb).strip():
                    return str(gb)
        except (OSError, ValueError):
            return ""
    return ""


# Wave 1rxyi: the distribution zip ships the single-use bootstrap `install-wavefoundry.md` at the ZIP
# ROOT (build_pack.py — the agent must discover it before .wavefoundry/ is known). It therefore
# extracts into the PROJECT ROOT on every install and upgrade (`unzip -o`/`extractall`). The prune step
# is MANIFEST-scoped to .wavefoundry/framework/ and never touches a root file, so the bootstrap file
# would otherwise linger after install and be re-dropped on every upgrade. Remove it after extraction —
# it is transient (the canonical install instructions live in docs/prompts/install-wavefoundry.prompt.md).
_ROOT_BOOTSTRAP_FILENAME = "install-wavefoundry.md"


def _remove_root_bootstrap_file(root: Path) -> None:
    """Delete the extracted root ``install-wavefoundry.md`` bootstrap file (wave 1rxyi).

    Fail-safe: a missing file is a no-op and an unlink error is logged and swallowed — this is cosmetic
    project-root hygiene and must never fail or gate the upgrade."""
    path = root / _ROOT_BOOTSTRAP_FILENAME
    try:
        if path.exists():
            path.unlink()
            _log(f"  Removed transient bootstrap file {_ROOT_BOOTSTRAP_FILENAME} from the project root.")
    except OSError as exc:  # non-fatal — never abort the upgrade over a cleanup unlink
        _log(f"  ⚠  Could not remove {_ROOT_BOOTSTRAP_FILENAME} (non-fatal): {exc}")


def _snapshot_pre_extract_versions(root: Path) -> dict[str, str]:
    """Snapshot all relevant framework version constants from the consumer's
    pre-existing index/graph state files. Returns a flat dict with keys
    `chunker_docs`, `chunker_code`, `walker`, `graph_builder` (any subset
    when the corresponding state isn't present)."""
    out: dict[str, str] = {}
    # Chunker + walker live in the index-state store's build snapshot
    chunker_versions = _snapshot_pre_extract_chunker_versions(root)
    if "docs" in chunker_versions:
        out["chunker_docs"] = chunker_versions["docs"]
    if "code" in chunker_versions:
        out["chunker_code"] = chunker_versions["code"]
    _bm = _read_index_build_meta(root)
    walker = _bm.get("walker_version")
    if isinstance(walker, (str, int)) and str(walker).strip():
        out["walker"] = str(walker)
    # Wave 1rvfx: graph builder version lives in the INSTALLED project graph state
    # (.wavefoundry/index/graph/), read via _read_installed_graph_builder_version. The old read pointed
    # at the retired framework-graph layer's dead path, so this transition never fired in production.
    gb = _read_installed_graph_builder_version(root)
    if gb:
        out["graph_builder"] = gb
    return out


def _detect_chunker_version_bump(
    pre_extract: dict[str, str], new_version: str,
) -> tuple[bool, tuple[str, str] | None]:
    """Backwards-compat helper: returns (bumped, transition) for chunker only.
    Used by existing 1p3ho v1 tests. New code should use
    `_detect_version_transitions` which covers all three constants."""
    if not pre_extract or not new_version:
        return False, None
    old_docs = pre_extract.get("docs", "")
    old_code = pre_extract.get("code", "")
    diff = (old_docs and old_docs != new_version) or (old_code and old_code != new_version)
    if not diff:
        return False, None
    old_for_display = old_docs or old_code or next(iter(pre_extract.values()), "")
    return True, (old_for_display, new_version)


def _detect_version_transitions(
    pre_extract: dict[str, str], root: Path,
) -> list[tuple[str, str, str]]:
    """Compare pre-extract snapshot against the just-extracted pack's version
    constants. Returns a list of `(constant_name, old, new)` for each
    transition detected. Empty list when nothing changed or no baseline."""
    transitions: list[tuple[str, str, str]] = []
    if not pre_extract:
        return transitions
    # Chunker (per-layer)
    new_chunker = _read_chunker_version_from_pack(root)
    if new_chunker:
        for layer in ("docs", "code"):
            old = pre_extract.get(f"chunker_{layer}", "")
            if old and old != new_chunker:
                transitions.append((f"CHUNKER_VERSION ({layer} index)", old, new_chunker))
    # Walker
    new_walker = _read_walker_version_from_pack(root)
    if new_walker:
        old = pre_extract.get("walker", "")
        if old and old != new_walker:
            transitions.append(("WALKER_VERSION", old, new_walker))
    # Graph builder
    new_graph = _read_graph_builder_version_from_pack(root)
    if new_graph:
        old = pre_extract.get("graph_builder", "")
        if old and old != new_graph:
            transitions.append(("GRAPH_BUILDER_VERSION", old, new_graph))
    return transitions


def _verify_chunker_rebuild_succeeded(root: Path) -> bool:
    """After Phase 4 ran, verify the docs index reflects the new chunker
    version. Backwards-compat helper retained for the existing test surface;
    no longer load-bearing in the upgrade flow (operator's direction: trust
    the indexer, just log)."""
    data = _read_index_build_meta(root)
    if not data:
        return True
    stored = data.get("chunker_versions") or {}
    if not isinstance(stored, dict) or "docs" not in stored:
        return True
    new_version = _read_chunker_version_from_pack(root)
    if not new_version:
        return True
    return str(stored.get("docs", "")) == new_version


# ── Extension hook model (12r1y) ─────────────────────────────────────────────

class UpgradeContext:
    """Context passed to every extension hook function.

    Hooks can inspect ``from_version`` and ``to_version`` to self-select.
    Use ``_to_version()`` from ``check_version`` for version-aware comparison
    (handles both semver and legacy date strings):

        from check_version import _to_version
        from packaging.version import Version

        def pre_surface_rendering(ctx):
            if ctx.from_version and _to_version(ctx.from_version) < Version("1.0.0"):
                # migration only needed when upgrading from before v1.0.0
                ...
    """

    def __init__(
        self,
        root: Path,
        from_version: str | None,
        to_version: str | None,
        zip_path: Path | None,
        yes: bool,
        dry_run: bool = False,
    ) -> None:
        self.root = root
        self.from_version = from_version
        self.to_version = to_version
        self.zip_path = zip_path
        self.yes = yes
        # Wave 1p3b9 (1p3b6): when True, post_extract migrations call their
        # `_preview_*` variants (zero filesystem mutations) and write a
        # preview-log instead of the action log. Propagated from the upgrade
        # orchestrator's --dry-run flag.
        self.dry_run = dry_run
        # Wave 1p3dk / 1p3ho: chunker-version transition tracking. Populated
        # before extract (pre_extract_chunker_versions) and after extract
        # (chunker_version_bumped, chunker_version_transition) so Phase 4 can
        # route to phase_index_rebuild instead of phase_index_update when the
        # consumer's existing index was built with an older CHUNKER_VERSION.
        # Closes the field failure mode where 1.5.0's chunker bump
        # didn't trigger a rebuild because the auto-escalate in build_index
        # was silent (no operator-visible decision) and unverified.
        self.pre_extract_chunker_versions: dict[str, str] = {}
        self.chunker_version_bumped: bool = False
        self.chunker_version_transition: tuple[str, str] | None = None

    def __repr__(self) -> str:
        return (
            f"UpgradeContext(from={self.from_version!r}, to={self.to_version!r}, "
            f"root={str(self.root)!r}, dry_run={self.dry_run!r})"
        )


def _load_extension_module(zip_path: Path | None) -> types.ModuleType | None:
    """Load ``upgrade_extensions.py`` from inside the zip without extracting it.

    The extension module is read from the *new* pack before any files are
    written to disk, so its ``pre_extract`` hook fires at the right time.

    Returns the loaded module, or ``None`` when:
    - no zip is provided (upgrading from current tree)
    - the zip contains no extension module
    - loading fails (logged as a warning — never fatal)
    """
    if zip_path is None:
        return None

    CANDIDATES = (
        ".wavefoundry/framework/scripts/upgrade_extensions.py",
        "framework/scripts/upgrade_extensions.py",
    )

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())
            for candidate in CANDIDATES:
                if candidate not in names:
                    continue
                source = zf.read(candidate).decode("utf-8")
                mod = types.ModuleType("upgrade_extensions")
                mod.__file__ = candidate
                try:
                    exec(compile(source, candidate, "exec"), mod.__dict__)
                except SyntaxError as exc:
                    _log(f"  ⚠  upgrade_extensions.py syntax error — skipping: {exc}")
                    return None
                except Exception as exc:  # noqa: BLE001
                    _log(f"  ⚠  upgrade_extensions.py load error — skipping: {exc}")
                    return None
                _log(f"  Extension module loaded from zip ({candidate}).")
                return mod
    except (OSError, zipfile.BadZipFile) as exc:
        _log(f"  ⚠  Could not open zip to load upgrade_extensions: {exc}")
    return None


def _run_hook(
    name: str,
    ctx: UpgradeContext,
    ext_mod: types.ModuleType | None,
) -> None:
    """Run a named hook through both the extension module and convention scripts.

    Layers are called in order — extension module first, convention script second.
    Both always run for a given hook name (additive, not exclusive).

    Hook names use underscores (``pre_surface_rendering``); convention script
    filenames use dashes (``pre-surface-rendering``).

    A hook failure (exception or non-zero exit) calls ``sys.exit(3)``.
    """
    # 1. Extension module hook
    if ext_mod is not None:
        hook_fn = getattr(ext_mod, name, None)
        if callable(hook_fn):
            try:
                hook_fn(ctx)
            except SystemExit:
                raise
            except Exception as exc:  # noqa: BLE001
                _err(f"Extension hook '{name}' raised: {exc}")
                sys.exit(3)

    # 2. Convention script: .wavefoundry/hooks/<name-with-dashes>
    script_name = name.replace("_", "-")
    hooks_dir = ctx.root / ".wavefoundry" / "hooks"
    # Wave 1p9hm: resolve the convention hook in an OS-aware way. On POSIX an extensionless executable
    # is run directly — os.access(X_OK) is meaningful there. On Windows os.access(X_OK) is a no-op
    # (True for any file) and an extensionless file cannot be spawned by path — the resulting OSError
    # previously escaped the TimeoutExpired-only except and crashed the upgrade. So on Windows prefer an
    # explicit `<name>.py` (run via the interpreter) or `<name>.cmd`/`.bat` (self-executable by
    # extension), and skip a bare extensionless hook with a warning rather than crashing.
    hook_cmd: list[str] | None = None
    if os.name == "nt":
        py_hook = hooks_dir / f"{script_name}.py"
        ext_hook = next(
            (hooks_dir / f"{script_name}{suffix}" for suffix in (".cmd", ".bat")
             if (hooks_dir / f"{script_name}{suffix}").exists()),
            None,
        )
        if py_hook.exists():
            hook_cmd = [_preferred_python(), str(py_hook)]
        elif ext_hook is not None:
            # Run the batch hook through `cmd /c` — isolated_run calls subprocess.run WITHOUT
            # shell=True, and Windows CreateProcess cannot launch a .cmd/.bat by path (it raises
            # WinError 193, which would escape the TimeoutExpired-only except and crash the upgrade —
            # the very crash class this branch exists to prevent).
            hook_cmd = ["cmd", "/c", str(ext_hook)]
        elif (hooks_dir / script_name).exists():
            _log(
                f"  Skipping convention hook '{script_name}': on Windows a hook needs a runnable "
                f"extension — add {script_name}.py or {script_name}.cmd."
            )
    else:
        hook_path = hooks_dir / script_name
        if hook_path.exists() and os.access(str(hook_path), os.X_OK):
            hook_cmd = [str(hook_path)]

    if hook_cmd is not None:
        env = {
            **os.environ,
            "WF_FROM_VERSION": ctx.from_version or "",
            "WF_TO_VERSION": ctx.to_version or "",
            "WF_ROOT": str(ctx.root),
            "WF_YES": "1" if ctx.yes else "0",
        }
        try:
            result = subprocess_util.isolated_run(
                hook_cmd, env=env, cwd=str(ctx.root),
                check=False, timeout=_HOOK_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            _err(
                f"Convention hook '{script_name}' timed out after "
                f"{_HOOK_TIMEOUT_S}s — aborting upgrade."
            )
            sys.exit(3)
        if result.returncode != 0:
            _err(
                f"Convention hook '{script_name}' exited {result.returncode} "
                "— aborting upgrade."
            )
            sys.exit(3)


# All known hook names in call order — used by dry-run to inventory convention hooks.
HOOK_NAMES = [
    "post_preflight",
    "pre_extract", "post_extract",
    "pre_surface_rendering", "post_surface_rendering",
    "pre_pruning", "post_pruning",
    "pre_docs_gate", "post_docs_gate",
    "pre_index_rebuild", "post_index_rebuild",
    "pre_cleanup", "post_cleanup",
]

# Convention hook subprocess timeout in seconds.
_HOOK_TIMEOUT_S = 300  # 5 minutes


def _is_interactive() -> bool:
    return sys.stdin.isatty()


def _confirm_proceed(yes: bool) -> bool:
    if yes or not _is_interactive():
        return True
    try:
        answer = input("Proceed? [y/N] ").strip().lower()
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def _run(cmd: list[str], root: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess_util.isolated_run(cmd, cwd=str(root), check=check)


# ── Dry-run (--dry-run / -n) ──────────────────────────────────────────────────

def _read_extension_source(zip_path: Path | None) -> tuple[str, str] | None:
    """Return ``(zip_entry_path, source_code)`` from the zip without executing.

    Returns ``None`` when the zip is absent, unreadable, or contains no
    ``upgrade_extensions.py``.  The source is returned as-is so callers can
    display or analyse it before the real upgrade runs.
    """
    if zip_path is None:
        return None
    candidates = (
        ".wavefoundry/framework/scripts/upgrade_extensions.py",
        "framework/scripts/upgrade_extensions.py",
    )
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())
            for candidate in candidates:
                if candidate in names:
                    return candidate, zf.read(candidate).decode("utf-8")
    except (OSError, zipfile.BadZipFile):
        pass
    return None


def _ensure_scripts_on_path() -> None:
    """Ensure SCRIPTS_DIR is importable so upgrade_lib and check_version can be imported.

    ``main()`` inserts SCRIPTS_DIR into sys.path before dispatching to phases.
    Phase functions that are called directly (e.g. from tests or dry-run) call
    this guard themselves so they are not coupled to the main() entry point.
    """
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))


def phase_dry_run(root: Path) -> int:
    """Print the full upgrade plan and hook inventory without touching anything on disk.

    Intended for agent-side safety review before committing to the real upgrade:
    the agent can inspect seed diffs, the extension module source, and every
    convention hook script, then decide whether to proceed.

    Exit codes: always 0 (dry-run never fails the upgrade).
    """
    _ensure_scripts_on_path()
    import upgrade_lib

    _log("\n── Dry Run ── (no changes will be made) ─────────────────────────────────")

    # Advisory lock check
    existing_lock = upgrade_lib.read_upgrade_lock(root)
    if existing_lock is not None:
        if upgrade_lib.is_lock_stale(root):
            _log("⚠  Stale upgrade lock detected (PID not running) — would be cleared on real run.")
        else:
            _log("⚠  Upgrade already in progress (lock file present and PID is running).")

    # Dashboard
    dash_running, dash_pid, dash_url = _detect_dashboard(root)
    if dash_running:
        _log(f"⚠  Dashboard is running (pid={dash_pid}, url={dash_url}) — would pause during upgrade.")

    # Versions
    from_version = _read_installed_revision(root)
    zip_path = _find_zip(root)
    if zip_path:
        to_version = _read_zip_version(zip_path) or "unknown"
    else:
        to_version = _read_pack_version(root) or "unknown"

    # Version direction (advisory)
    from check_version import compare_versions
    if from_version and to_version and to_version != "unknown":
        direction = compare_versions(to_version, from_version)
        if direction == "downgrade":
            _log(
                f"⚠  WOULD ABORT: pack downgrade detected "
                f"(installed={from_version}, pack={to_version})."
            )

    # Change plan
    prompt_files = _detect_prompt_files(root)
    seed_diffs = _compute_seed_diffs(root, zip_path) if zip_path else None
    _print_change_plan(
        root=root,
        from_version=from_version,
        to_version=to_version,
        zip_path=zip_path,
        dash_running=dash_running,
        prompt_files=prompt_files,
        seed_diffs=seed_diffs,
    )

    # ── Hook inventory ────────────────────────────────────────────────────────
    _log("── Hook Inventory ──────────────────────────────────────────────────────")

    # Extension module source
    ext_entry = _read_extension_source(zip_path)
    if zip_path is None:
        _log("\nExtension module:   n/a (no zip)")
    elif ext_entry is None:
        _log("\nExtension module:   none (upgrade_extensions.py not in zip)")
    else:
        candidate, source = ext_entry
        _log(f"\n── Extension module: {candidate} ──")
        _log(source.rstrip())
        _log("── End extension module ──")

    # Convention hooks
    hooks_dir = root / ".wavefoundry" / "hooks"
    found: list[tuple[str, Path]] = []
    for hook_name in HOOK_NAMES:
        script_name = hook_name.replace("_", "-")
        hook_path = hooks_dir / script_name
        if hook_path.exists():
            found.append((script_name, hook_path))

    if not found:
        _log("\nConvention hooks:   none (.wavefoundry/hooks/<name> scripts absent)")
    else:
        _log(f"\nConvention hooks:   {len(found)} found")
        for script_name, hook_path in found:
            _log(f"\n── Convention hook: {hook_path} ──")
            try:
                _log(hook_path.read_text(encoding="utf-8").rstrip())
            except OSError as exc:
                _log(f"  (could not read: {exc})")
            _log(f"── End {script_name} ──")

    # Wave 1p3b9 (1p3b6): migration preview. When the new pack's
    # upgrade_extensions.py defines `post_extract`, call it with
    # `dry_run=True` so its preview helpers fire without mutating state.
    # The preview log lands at `.wavefoundry/logs/upgrade-migration-1.5.0.preview.log`
    # with a distinct filename from the real-run log so a subsequent real
    # run's report does not shadow it. Operators can review the planned
    # actions before committing.
    if zip_path is not None:
        ext_module = _load_extension_module(zip_path)
        if ext_module is not None and hasattr(ext_module, "post_extract"):
            preview_ctx = UpgradeContext(
                root=root,
                from_version=from_version,
                to_version=to_version if to_version != "unknown" else None,
                zip_path=zip_path,
                yes=True,
                dry_run=True,
            )
            _log("\n── Migration preview (post_extract, dry_run=True) ──")
            try:
                ext_module.post_extract(preview_ctx)
            except Exception as exc:
                _log(f"  (preview failed: {exc})")
            preview_log = root / ".wavefoundry" / "logs" / "upgrade-migration-1.5.0.preview.log"
            if preview_log.is_file():
                _log(f"  preview log: {preview_log}")
                try:
                    _log(preview_log.read_text(encoding="utf-8").rstrip())
                except OSError as exc:
                    _log(f"  (could not read preview log: {exc})")
            else:
                _log("  no planned actions (dry-run produced no preview log)")
            _log("── End migration preview ──")

    _log("\n── End Dry Run ──────────────────────────────────────────────────────────")
    _log("No changes were made. Run without --dry-run to execute the upgrade.")
    return 0


# ── Phase 0 — Pre-flight ──────────────────────────────────────────────────────

def _clear_stale_upgrade_lock_for_preflight(root: Path, upgrade_lib: Any) -> None:
    """Clear ordinary stale locks, but retain failed dashboard restart intent."""
    existing_lock = upgrade_lib.read_upgrade_lock(root)
    if existing_lock is None or not upgrade_lib.is_lock_stale(root):
        return
    if (
        existing_lock.get("failed_phase")
        and existing_lock.get("dashboard_restart_pending")
    ):
        _log(
            "⚠  Failed upgrade lock detected (PID not running) — "
            "preserving dashboard restart intent for the recovery run."
        )
        return
    _log("⚠  Stale upgrade lock detected (PID not running) — clearing it.")
    upgrade_lib.remove_upgrade_lock(root)


def phase_preflight(root: Path, yes: bool) -> tuple[str | None, str | None, Path | None]:
    """Run pre-flight checks, compute seed diffs, and print change plan.

    Returns (from_version, to_version, zip_path).
    Exits with code 3 on any blocking pre-flight failure.
    """
    import upgrade_lib

    # Check for existing lock
    existing_lock = upgrade_lib.read_upgrade_lock(root)
    if existing_lock is not None:
        if upgrade_lib.is_lock_stale(root):
            _clear_stale_upgrade_lock_for_preflight(root, upgrade_lib)
        else:
            _err(
                "Upgrade already in progress (upgrade-in-progress.json exists and PID is running).\n"
                f"  Lock: {upgrade_lib.upgrade_lock_path(root)}\n"
                "  If the previous upgrade crashed, remove the lock manually:\n"
                f"    rm {upgrade_lib.upgrade_lock_path(root)}"
            )
            sys.exit(3)

    # Dashboard check
    dash_running, dash_pid, dash_url = _detect_dashboard(root)
    if dash_running:
        _log(f"⚠  Dashboard is running (pid={dash_pid}, url={dash_url}) — it will pause during upgrade.")

    # Installed revision
    from_version = _read_installed_revision(root)

    # Detect zip
    zip_path = _find_zip(root)
    if zip_path:
        zip_version = _read_zip_version(zip_path) or "unknown"
        to_version = zip_version
    else:
        # No zip — upgrading using the current tree as-is
        to_version = _read_pack_version(root) or "unknown"
        zip_path = None

    # Version guard (R4)
    from check_version import compare_versions
    if from_version and to_version and to_version != "unknown":
        direction = compare_versions(to_version, from_version)
        if direction == "downgrade":
            _err(
                f"Pack downgrade detected: installed={from_version}, pack={to_version}.\n"
                "Downgrade is not supported. To force, manually unzip and run phases individually."
            )
            sys.exit(3)

    # Upgrade floor (1p5do): WARN — do not block — when upgrading from below the supported floor.
    if from_version and _below_upgrade_floor(from_version):
        _log(
            f"  WARNING: installed version {from_version!r} is below the supported upgrade "
            f"floor {SUPPORTED_UPGRADE_FLOOR}. Migrations for transitions older than 1.4→1.5 "
            "have been pruned, so this jump may skip an intermediate migration. Proceeding — "
            "verify the result, or upgrade in steps if anything looks off."
        )

    # Prompt file detection (R9)
    prompt_files = _detect_prompt_files(root)

    # Seed diff (12r1b) — computed from zip vs disk before any extraction.
    # None means "no zip" (→ "n/a" in plan); [] means "zip present, nothing changed".
    seed_diffs = _compute_seed_diffs(root, zip_path) if zip_path else None

    # Change plan (R6)
    _print_change_plan(
        root=root,
        from_version=from_version,
        to_version=to_version,
        zip_path=zip_path,
        dash_running=dash_running,
        prompt_files=prompt_files,
        seed_diffs=seed_diffs,
    )

    if not _confirm_proceed(yes):
        _log("Aborted.")
        sys.exit(0)

    return from_version, to_version, zip_path


def _print_change_plan(
    root: Path,
    from_version: str | None,
    to_version: str | None,
    zip_path: Path | None,
    dash_running: bool,
    prompt_files: list[str],
    seed_diffs: list[tuple[str, str, str]] | None = None,
) -> None:
    _log("")
    _log("Wavefoundry Upgrade Plan")
    _log("=" * 40)
    _log(f"Pack version:       {to_version or '(unknown)'}")
    _log(f"Installed revision: {from_version or '(none)'}")
    if zip_path:
        _log(f"Zip to apply:       {zip_path.name}")
    else:
        _log("Zip to apply:       none (using current tree)")
    _log("Surfaces to render: hooks, MCP config, bin launchers, agent surfaces")
    if from_version:
        _log(f"Prune mode:         MANIFEST diff (old={from_version})")
    else:
        _log("Prune mode:         legacy removal list (no prior MANIFEST)")
    _log("Docs gate:          .wavefoundry/bin/wf docs-gardener && .wavefoundry/bin/wf docs-lint")
    if dash_running:
        _log("Dashboard:          running — will pause during upgrade, auto-restart after")
    else:
        _log("Dashboard:          not running")
    if prompt_files:
        _log("Prompt files needing .prompt.md rename:")
        for f in prompt_files:
            _log(f"  {f}")
    else:
        _log("Prompt files:       none (all already use .prompt.md extension)")

    # Seed diff summary
    if seed_diffs is None:
        _log("Seeds changed:      n/a (no zip — current tree already applied)")
    elif not seed_diffs:
        _log("Seeds changed:      none")
    else:
        n_modified = sum(1 for _, s, _ in seed_diffs if s == "modified")
        n_added = sum(1 for _, s, _ in seed_diffs if s == "added")
        n_removed = sum(1 for _, s, _ in seed_diffs if s == "removed")
        parts = []
        if n_modified:
            parts.append(f"{n_modified} modified")
        if n_added:
            parts.append(f"{n_added} added")
        if n_removed:
            parts.append(f"{n_removed} removed")
        _log(f"Seeds changed:      {len(seed_diffs)} ({', '.join(parts)})")

    _log("")

    # Full seed diffs — emitted after the plan table so the agent can act on them
    if seed_diffs:
        _log("── Seed Diffs ──────────────────────────────────────────────────────────")
        for filename, status, diff_text in seed_diffs:
            _log(f"\n── Seed diff: {filename} [{status}] ──")
            _log(diff_text.rstrip())
        _log("\n── End Seed Diffs ──────────────────────────────────────────────────────")
        _log("")


# ── Phase 1 — Surface rendering ───────────────────────────────────────────────

def phase_surface_rendering(root: Path) -> None:
    _log("\n── Phase 1: Surface rendering ──")
    # Wave 1p88t (1p7pb-adr): VERIFY the committed `command: "python3"` launchers resolve on every
    # upgrade (detect + guide — no shim/symlink creation, no PATH edit). strict=False — warn
    # (non-fatal) if `python3` does not resolve; the upgrade does not abort on it.
    try:
        venv_bootstrap.ensure_python_resolves(strict=False)
    except Exception:
        pass
    script = SCRIPTS_DIR / "render_platform_surfaces.py"
    if not script.exists():
        _log("  render_platform_surfaces.py not found — skipping surface rendering.")
        return
    result = subprocess_util.isolated_run(
        [_preferred_python(), str(script), "--repo-root", str(root)],
        cwd=str(root),
        check=False,
    )
    if result.returncode != 0:
        _err("Surface rendering failed.")
        sys.exit(2)
    _log("  Surfaces rendered.")


# ── Phase 2 — Pruning ─────────────────────────────────────────────────────────

def _remove_deprecated_framework_index(root: Path) -> bool:
    """1p5ik: `.wavefoundry/framework/index/` is a deprecated pre-1p4ww artifact — the framework
    index layer was removed (framework content now folds into the project docs index) and no pack
    ships it. Manifest-prune cannot remove it (index `.lance` files were never in any MANIFEST), so
    remove it explicitly. Called from `phase_cleanup` AFTER the index rebuild — not the prune phase —
    because a live index `update` can run on the OLD code earlier in the upgrade (before the new code
    is in effect) and re-create the directory; only after the rebuild lands on the new code (which
    never touches it) is removal durable. Returns True when a directory was removed; a no-op (no
    error) when absent. Safe: every framework-layer read path is dead, and the self-host has none."""
    stale = root / ".wavefoundry" / "framework" / "index"
    if not stale.is_dir():
        return False
    # Wave 1p6d6: on Windows a read-only (or memory-mapped) child file makes shutil.rmtree raise,
    # so the bare rmtree left the deprecated dir in place. Clear the read-only attribute and retry
    # the failing op. POSIX is unaffected (no read-only-blocks-delete semantics there).
    def _clear_readonly_and_retry(func, path, _exc):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except OSError:
            pass
    _rm_kw = ({"onexc": _clear_readonly_and_retry} if sys.version_info >= (3, 12)
              else {"onerror": _clear_readonly_and_retry})
    try:
        shutil.rmtree(stale, **_rm_kw)
        _log("  Removed stale .wavefoundry/framework/index/ (deprecated pre-1p4ww framework index).")
        return True
    except OSError as exc:
        _log(f"  Could not remove stale .wavefoundry/framework/index/ ({exc}) — continuing.")
        return False


def phase_pruning(root: Path) -> int:
    """Run prune_framework.py.  Returns number of files pruned."""
    _log("\n── Phase 2: Pruning ──")
    script = SCRIPTS_DIR / "prune_framework.py"
    if not script.exists():
        _log("  prune_framework.py not found — skipping pruning.")
        return 0
    cmd = [_preferred_python(), str(script)]
    if OLD_MANIFEST_TMP.exists():
        cmd += ["--old-manifest", str(OLD_MANIFEST_TMP)]
    # Wave 1p8gv: capture as UTF-8 (errors=replace) so prune's non-ASCII output decodes cleanly on a
    # cp1252 Windows console (folded into the shared helper).
    result = subprocess_util.isolated_run(cmd, cwd=str(root), capture_output=True, text=True, check=False)
    if result.stdout:
        _log(result.stdout.rstrip())
    if result.returncode != 0:
        _log(f"  Pruning exited {result.returncode} — continuing (non-fatal).")
        return 0
    # Wave 1p44q — read the authoritative count from prune_framework.py's stderr
    # summary ("prune: deleted N item(s)" / "prune: would delete N item(s)").
    # The old heuristic scanned stdout for "removed"/"pruned", but the per-file
    # stdout lines say "deleted:" / "[dry-run] would delete:" — neither substring —
    # so the count was structurally always 0.
    pruned = 0
    m = _re.search(r"prune:\s+(?:would delete|deleted)\s+(\d+)\s+item", result.stderr or "")
    if m:
        pruned = int(m.group(1))
    _log(f"  Pruning complete — {pruned} item(s) pruned.")
    return pruned


# ── Phase 3 — Docs gate ───────────────────────────────────────────────────────

def _atomic_write_text(path: Path, text: str, label: str) -> None:
    """Atomically replace one UTF-8 text file beside its destination."""

    temp = path.with_name(f".{path.name}.{os.getpid()}.{label}.tmp")
    try:
        temp.write_text(text, encoding="utf-8", newline="")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def phase_review_status_projection(root: Path) -> dict[str, int]:
    """Compact adopted wave review state through the canonical projection.

    Historical prose outside the owned block is byte-preserved.  A malformed
    adopted ledger/marker fails the upgrade; non-adopted closed waves are
    reported only.  Active/readied prose-only authority is not guessed.
    """

    import re

    from review_evidence import (
        externalize_adopted_inline_wave_locked,
        parse_review_evidence_source,
        render_review_evidence_projection,
        render_review_status_projection,
        required_review_status_keys,
        review_event_write_lock,
        validate_external_review_evidence,
    )

    counts = {
        "projected": 0,
        "adopted_inline": 0,
        "reported_legacy": 0,
        "blocked_legacy": 0,
    }
    blocked_legacy_waves: list[str] = []
    waves_dir = root / "docs" / "waves"
    if not waves_dir.is_dir():
        return counts
    try:
        root_real = root.resolve(strict=True)
    except OSError as exc:
        raise SystemExit(f"cannot resolve upgrade root for review projection: {exc}")
    with review_event_write_lock(root):
        for wave_dir in sorted(path for path in waves_dir.iterdir() if path.is_dir()):
            try:
                wave_real = wave_dir.resolve(strict=True)
            except OSError as exc:
                raise SystemExit(
                    f"{wave_dir.name}: cannot resolve wave directory safely: {exc}"
                )
            if wave_dir.is_symlink() or not wave_real.is_relative_to(root_real):
                raise SystemExit(
                    f"{wave_dir.name}: review projection wave directory escapes "
                    "the repository root through a symlink"
                )
            wave_md = wave_dir / "wave.md"
            if not wave_md.is_file():
                continue
            try:
                wave_md_real = wave_md.resolve(strict=True)
            except OSError as exc:
                raise SystemExit(
                    f"{wave_dir.name}: cannot resolve wave.md safely: {exc}"
                )
            if wave_md.is_symlink() or not wave_md_real.is_relative_to(wave_real):
                raise SystemExit(
                    f"{wave_dir.name}: review projection wave.md escapes its "
                    "wave directory through a symlink"
                )
            ledger = wave_dir / "events.jsonl"
            if ledger.is_symlink():
                raise SystemExit(
                    f"{wave_dir.name}: review projection events.jsonl may not "
                    "be a symlink"
                )
            if ledger.exists():
                try:
                    ledger_real = ledger.resolve(strict=True)
                except OSError as exc:
                    raise SystemExit(
                        f"{wave_dir.name}: cannot resolve events.jsonl safely: {exc}"
                    )
                if not ledger_real.is_relative_to(wave_real):
                    raise SystemExit(
                        f"{wave_dir.name}: review projection events.jsonl escapes "
                        "its wave directory"
                    )
            text = wave_md.read_text(encoding="utf-8")
            source, source_errors = parse_review_evidence_source(text)
            status_match = re.search(r"(?mi)^Status:\s*(\S+)", text)
            status = status_match.group(1).lower() if status_match else ""
            active = status in {"planned", "readied", "ready", "active", "implementing"}
            adopted_records = None
            if source_errors:
                raise SystemExit(
                    f"{wave_dir.name}: malformed review-evidence source: "
                    + "; ".join(source_errors)
                )
            if source is None:
                adopted_records, adoption_error = externalize_adopted_inline_wave_locked(
                    root,
                    wave_dir.name,
                    wave_md,
                )
                if adoption_error:
                    raise SystemExit(
                        f"{wave_dir.name}: typed-inline review evidence adoption failed: "
                        f"{adoption_error}"
                    )
                if adopted_records is not None:
                    counts["adopted_inline"] += 1
                    text = wave_md.read_text(encoding="utf-8")
                    source = "events.jsonl"
                if active and "## Review Evidence" in text:
                    if source is None:
                        counts["blocked_legacy"] += 1
                        blocked_legacy_waves.append(wave_dir.name)
                        continue
                if source is None:
                    counts["reported_legacy"] += 1
                    continue
            if source == "events.jsonl" and adopted_records is not None:
                records = adopted_records
            else:
                validation = validate_external_review_evidence(wave_md)
                if validation.errors:
                    raise SystemExit(
                        f"{wave_dir.name}: invalid canonical events.jsonl: "
                        + "; ".join(validation.errors)
                    )
                records = validation.records
            projected = render_review_evidence_projection(text, records)
            projected = render_review_status_projection(
                projected,
                records,
                required_review_status_keys(root, projected, records),
            )
            if projected != text:
                _atomic_write_text(wave_md, projected, "review-status-projection")
                counts["projected"] += 1
    if blocked_legacy_waves:
        raise SystemExit(
            "active/readied prose-only review evidence cannot be adopted losslessly "
            "for: "
            + ", ".join(blocked_legacy_waves)
            + ". Record canonical typed evidence with wf_review_evidence, "
            "then rerun `wf upgrade`; arbitrary review prose is never parsed as "
            "approval authority. External-ledger waves were still projected before "
            "this action-required report."
        )
    return counts


def phase_docs_gate(root: Path) -> None:
    _log("\n── Phase 3: Docs gate ──")
    # Wave 1p7tz: the `bin/docs-gardener`/`bin/docs-lint` wrappers were retired (the cross-OS `wf`
    # dispatcher replaced them), so run the scripts directly under the venv interpreter.
    for label, py_name in [("docs-gardener", "docs_gardener.py"), ("docs-lint", "docs_lint.py")]:
        py_script = SCRIPTS_DIR / py_name
        if not py_script.exists():
            _log(f"  {label} not found — skipping.")
            continue
        result = subprocess_util.isolated_run([_preferred_python(), str(py_script)], cwd=str(root), check=False)
        if result.returncode != 0:
            _err(f"Docs gate failed: {label} exited {result.returncode}")
            sys.exit(1)

    _log("  Docs gate: PASSED")


# ── Phase 4 — Index update / rebuild ──────────────────────────────────────────

def phase_index_update(root: Path) -> None:
    """Incremental index update — re-embeds only changed files.

    Auto-escalates to a full rebuild when chunker or embedding model version
    changed.  Use when source files have been edited but the format is stable.
    """
    _log("\n── Phase 4: Index update ──")
    setup_script = SCRIPTS_DIR / "setup_index.py"
    if not setup_script.exists():
        _log("  setup_index.py not found — skipping index update.")
        return

    _log("  Phase 4a: updating docs index (blocking) ...")
    memory_run_id = os.environ.get(
        "WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID", ""
    ).strip()
    child_env = None
    if memory_run_id:
        child_env = dict(os.environ)
        child_env["WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID"] = str(memory_run_id)
    result = subprocess_util.isolated_run(
        [_preferred_python(), str(setup_script), "--root", str(root)],
        cwd=str(root),
        check=False,
        env=child_env,
    )
    if result.returncode != 0:
        message = f"Docs index update exited {result.returncode}"
        if memory_run_id:
            raise RuntimeError(
                message
                + " — historical-memory publication remains incomplete and retryable"
            )
        _log(f"  ⚠  {message} — continuing.")

    # Phase 4b: update the GRAPH index too (blocking; graph-only is fast, ~seconds,
    # no embedding). Symmetric with the semantic update: `--graph-only` (no --full)
    # is an UPDATE that auto-escalates to a full re-extract when GRAPH_BUILDER_VERSION
    # advanced (graph_indexer's version check) — so a graph-builder bump materializes
    # during the upgrade instead of waiting for the first-query lazy rebuild.
    _log("  Phase 4b: updating graph index (blocking) ...")
    followup_env = subprocess_util.utf8_child_env()
    followup_env.pop("WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID", None)
    graph_result = subprocess_util.isolated_run(
        [_preferred_python(), str(setup_script), "--root", str(root), "--graph-only"],
        cwd=str(root),
        check=False,
        env=followup_env,
    )
    if graph_result.returncode != 0:
        _log(f"  ⚠  Graph index update exited {graph_result.returncode} — continuing (first-query rebuild remains the safety net).")

    if memory_run_id:
        _log(
            "  Phase 4c: skipped — the receipt-owned foreground pass already "
            "converged both semantic layers."
        )
        return

    _log("  Phase 4c: launching code index update in background ...")
    background_cmd = [
        _preferred_python(), str(setup_script),
        "--root", str(root),
        "--background-code",
    ]
    # H1 (Phase 4b reliability): log the launcher's output (docs build + any startup crash) to a
    # dedicated file instead of DEVNULL — the silent-failure case the JS/TS team hit had no
    # diagnosable trace. The detached code build (process B) logs separately to project-background-build.log.
    _bg_log = root / ".wavefoundry" / "logs" / "project-upgrade-bgcode.log"
    _bg_log.parent.mkdir(parents=True, exist_ok=True)
    _bg_log_file = open(_bg_log, "w", encoding="utf-8")  # noqa: SIM115
    # Wave 1p8gu: route through the shared isolated Popen — keeps the log-file stdout/stderr while it
    # supplies detached stdin + the detached/no-window Windows creationflags (no flashing console).
    try:
        subprocess_util.isolated_popen(
            background_cmd,
        stdout=_bg_log_file,
        stderr=_bg_log_file,
        cwd=str(root),
        env=followup_env,  # 1p8gv: UTF-8 stdio in the child (cp1252 safety)
        )
    finally:
        _bg_log_file.close()
    _log(f"  Code index update running in background (launcher log: {_bg_log}).")


def phase_index_rebuild(root: Path) -> None:
    """Full index rebuild — re-embeds every file from scratch.

    Use when a chunker version bump, embedding model change, or index corruption
    requires starting fresh.  Prefer phase_index_update for normal upgrades.
    """
    _log("\n── Phase 4: Index rebuild (full) ──")
    setup_script = SCRIPTS_DIR / "setup_index.py"
    if not setup_script.exists():
        _log("  setup_index.py not found — skipping index rebuild.")
        return

    _log("  Phase 4a: rebuilding docs index (blocking) ...")
    result = subprocess_util.isolated_run(
        [_preferred_python(), str(setup_script), "--root", str(root), "--full"],
        cwd=str(root),
        check=False,
    )
    if result.returncode != 0:
        _log(f"  ⚠  Docs index rebuild exited {result.returncode} — continuing.")

    # Phase 4b: rebuild the GRAPH index too (blocking; fast, no embedding) —
    # symmetric with the semantic full rebuild.
    _log("  Phase 4b: rebuilding graph index (blocking) ...")
    graph_result = subprocess_util.isolated_run(
        [_preferred_python(), str(setup_script), "--root", str(root), "--graph-only", "--full"],
        cwd=str(root),
        check=False,
    )
    if graph_result.returncode != 0:
        _log(f"  ⚠  Graph index rebuild exited {graph_result.returncode} — continuing (first-query rebuild remains the safety net).")

    _log("  Phase 4c: launching code index rebuild in background ...")
    background_cmd = [
        _preferred_python(), str(setup_script),
        "--root", str(root),
        "--background-code",
        "--full",
    ]
    # H1 (Phase 4b reliability): log the launcher's output instead of DEVNULL (see phase_index_update).
    _bg_log = root / ".wavefoundry" / "logs" / "project-upgrade-bgcode.log"
    _bg_log.parent.mkdir(parents=True, exist_ok=True)
    _bg_log_file = open(_bg_log, "w", encoding="utf-8")  # noqa: SIM115
    # Wave 1p8gu: route through the shared isolated Popen (see phase_index_update).
    try:
        subprocess_util.isolated_popen(
            background_cmd,
            stdout=_bg_log_file,
            stderr=_bg_log_file,
            cwd=str(root),
            env=subprocess_util.utf8_child_env(),  # 1p8gv: UTF-8 stdio in the child (cp1252 safety)
        )
    finally:
        _bg_log_file.close()
    _log(f"  Code index rebuild running in background (launcher log: {_bg_log}).")


# ── Phase 5 — Cleanup & summary ───────────────────────────────────────────────

def phase_cleanup(
    root: Path,
    from_version: str | None,
    to_version: str | None,
    zip_path: Path | None,
    pruned_count: int,
    ran_index_rebuild: bool,
    failed_phase: str | None = None,
    lock_present: bool = True,
) -> None:
    import upgrade_lib

    _log("\n── Phase 5: Cleanup ──")
    if not lock_present:
        # Wave 1p44o — there is no upgrade lock to clean up. Do NOT print an
        # all-defaults "Upgrade complete" summary (Version: (none) → (unknown),
        # Files pruned: 0) as if a real upgrade had happened; that misleads the
        # operator into thinking a phantom upgrade completed.
        _log("  ⚠  No upgrade lock found — nothing to clean up.")
        _log("     The upgrade may not have run, or cleanup already completed.")
        return

    lock_state = upgrade_lib.read_upgrade_lock(root) or {}
    restart_pending = bool(lock_state.get("dashboard_restart_pending"))
    restart_port = lock_state.get("dashboard_restart_port")
    if failed_phase:
        _log(
            f"  Upgrade lock retained — it carries a failure marker (phase: "
            f"{failed_phase}) and the tree may be half-replaced."
        )
        if restart_pending:
            _log(
                "  Dashboard restart intent retained; it will run only after a "
                "successful recovery cleanup."
            )
        if failed_phase in {"review_status_projection", "docs_gate"}:
            _log(
                "  Resolve the typed review-state or docs findings, run "
                "--resume-after-gate, then --update-index and --cleanup."
            )
        else:
            _log("  Re-run the full upgrade to restore a clean state.")
        _print_operator_summary(
            from_version=from_version,
            to_version=to_version,
            zip_path=zip_path,
            pruned_count=pruned_count,
            ran_index_rebuild=ran_index_rebuild,
            failed_phase=failed_phase,
            root=root,
        )
        raise SystemExit(1)

    if restart_pending:
        try:
            import server_impl

            previous = os.environ.get("WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER")
            os.environ["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = "1"
            try:
                restart = server_impl.wf_start_dashboard_response(
                    root,
                    port=restart_port if isinstance(restart_port, int) else None,
                )
            finally:
                if previous is None:
                    os.environ.pop("WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER", None)
                else:
                    os.environ["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = previous
            if restart.get("status") != "ok":
                raise RuntimeError("dashboard restart returned an error")
            upgrade_lib.update_upgrade_lock(root, dashboard_restart_pending=False)
            _log("  Dashboard restarted on the pre-upgrade port.")
        except Exception as exc:
            upgrade_lib.update_upgrade_lock(
                root,
                failed_phase="dashboard_restart",
                failed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
            _err(
                f"Dashboard restart failed; upgrade lock retained for recovery: {exc}"
            )
            raise SystemExit(1)

    upgrade_lib.remove_upgrade_lock(root)
    _log("  Upgrade lock removed — dashboard will trigger post-upgrade reindex.")

    _warn_if_background_code_incomplete(root)
    _warn_if_migration_errors(root)
    # 1p5ik: remove the deprecated framework/index/ HERE, in cleanup (after the index rebuild), not
    # earlier in the prune phase. A live index "update" can run on the OLD code during the upgrade —
    # before the new code is in effect — and re-create framework/index/; only after the rebuild lands
    # on the new code (which never touches it) is removal durable. manifest-prune can't remove it
    # (its `.lance` files were never in MANIFEST), so this explicit step is the only thing that does.
    _remove_deprecated_framework_index(root)

    # Wave 1p601: map regen is decoupled from the index build, so a fresh upgrade
    # would otherwise never generate docs/references/codebase-map.md (field report).
    # Regenerate it once here, after the index phase, fail-safe — a generator error
    # must never fail the upgrade. ``generate_safe`` is change-only/idempotent.
    _regenerate_codebase_map_on_upgrade(root)
    # End-of-upgrade lifecycle-policy backstop (operator directive): Phase 2c
    # already provisioned scheme v2 earlier in the pipeline; re-verify here at
    # reconciliation time and heal via the idempotent materialization if it
    # somehow did not land (soft failure, out-of-band edit, or a transition
    # upgrade that ran an older pipeline without Phase 2c).
    _ensure_lifecycle_policy_backstop(root)

    _print_operator_summary(
        from_version=from_version,
        to_version=to_version,
        zip_path=zip_path,
        pruned_count=pruned_count,
        ran_index_rebuild=ran_index_rebuild,
        failed_phase=failed_phase,
        root=root,
    )


def _ensure_lifecycle_policy_backstop(root: Path) -> None:
    """Reconciliation-time re-check that the scheme-v2 lifecycle policy landed.

    Calls the idempotent ``materialize_lifecycle_policy``: a repo Phase 2c
    already provisioned is a no-op; an un-provisioned repo (Phase 2c soft
    failure, out-of-band edit mid-upgrade, or a transition upgrade whose old
    pipeline predated Phase 2c) is healed here. Fail-safe — a backstop error
    must never fail cleanup; it degrades to a loud pointer at the recovery
    command.
    """
    try:
        msg = materialize_lifecycle_policy(root)
    except RuntimeError as exc:
        _log(
            f"  ⚠  Lifecycle policy check: {exc}\n"
            "     Fix the config, then run `wf upgrade --materialize-lifecycle-policy`."
        )
        return
    if "left unchanged" in msg:
        _log("  Lifecycle policy check: scheme v2 present — OK.")
    else:
        _log(f"  Lifecycle policy check (backstop healed): {msg}")


def _regenerate_codebase_map_on_upgrade(root: Path) -> None:
    """Fail-safe one-shot codebase-map regen on upgrade (wave 1p601).

    Map regen is decoupled from the index build, so a fresh upgrade would never
    produce docs/references/codebase-map.md without this explicit call. Loaded via
    importlib (registered in sys.modules so dataclass annotations resolve); all
    exceptions are swallowed — regenerating the map must NEVER fail the upgrade.
    """
    try:
        import importlib.util as _ilu

        mod = sys.modules.get("gen_codebase_map")
        if mod is None:
            spec = _ilu.spec_from_file_location(
                "gen_codebase_map", SCRIPTS_DIR / "gen_codebase_map.py"
            )
            if not (spec and spec.loader):
                return
            mod = _ilu.module_from_spec(spec)
            sys.modules["gen_codebase_map"] = mod
            spec.loader.exec_module(mod)
        if mod.generate_safe(root):
            _log("  Codebase map refreshed → docs/references/codebase-map.md")
    except Exception as exc:  # noqa: BLE001 — fail-safe: never break the upgrade
        _log(f"  Codebase map refresh skipped ({exc}).")


def _warn_if_background_code_incomplete(root: Path) -> None:
    """H1 (Phase 4b reliability): warn when the BACKGROUND code re-embed left the code layer behind the
    (synchronously-built) docs layer — the silent-failure case (status 'idle', code chunker stale) the
    JS/TS team hit on p4g3/p4su. A stale code layer must not be mistaken for a finished upgrade."""
    meta = _read_index_build_meta(root)
    if not meta:
        return
    cv = meta.get("chunker_versions") or {}
    docs_v, code_v = cv.get("docs"), cv.get("code")
    if docs_v and code_v and str(docs_v) != str(code_v):
        _log(
            f"  ⚠  Code index chunker version ({code_v}) is still BEHIND the docs layer ({docs_v}) — "
            "the background code build (Phase 4b) may have failed or not yet finished."
        )
        _log(
            "     Check .wavefoundry/logs/project-background-build.log + project-upgrade-bgcode.log, "
            "then run: index_build(content='code', mode='rebuild')"
        )


def _below_upgrade_floor(from_version: str) -> bool:
    """1p5do: True when ``from_version`` is below ``SUPPORTED_UPGRADE_FLOOR`` or is unparseable
    (``compare_versions`` raises ValueError) — in both cases we can't confirm the pruned migration
    chain covers the transition, so the caller warns."""
    from check_version import compare_versions
    try:
        return compare_versions(from_version, SUPPORTED_UPGRADE_FLOOR) == "downgrade"
    except ValueError:
        return True


def _warn_if_no_version_baseline(pre_extract: dict, root: Path) -> bool:
    """1p5do: when an index exists but there is no version baseline to compare against (index/graph
    state absent or unreadable), _detect_version_transitions can't detect a bump and would go silent
    exactly when the rebuild signal matters most. Surface it anyway. Returns True when it warned."""
    if not pre_extract and (root / ".wavefoundry" / "index").is_dir():
        _log(
            "\n⚠  No framework version baseline found (index/graph state absent) — cannot "
            "detect version transitions. Phase 4 may run a full re-embed / graph re-extract."
        )
        return True
    return False


def _warn_if_migration_errors(root: Path) -> None:
    """1p5do: the post_extract migrations (convergence + 1.4→1.5) isolate their own failures to a
    report log and continue WITHOUT setting ``failed_phase``, so the summary can read 'Docs gate:
    PASSED' over a partially-failed migration. Scan the real (non-preview) migration logs for
    ``ERROR:`` records and surface a warning pointing at them so a green summary can't mask them."""
    import glob as _glob
    logs_dir = root / ".wavefoundry" / "logs"
    if not logs_dir.is_dir():
        return
    flagged: set[str] = set()
    for pattern in ("upgrade-migration-*.log", "upgrade-convergence-migration.log"):
        for path_str in _glob.glob(str(logs_dir / pattern)):
            name = Path(path_str).name
            if ".preview." in name:  # dry-run preview reports are not real migrations
                continue
            try:
                text = Path(path_str).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if any("ERROR:" in line for line in text.splitlines()):
                flagged.add(name)
    if flagged:
        _log(
            "  ⚠  Migration log(s) recorded ERROR entries: " + ", ".join(sorted(flagged)) + ". "
            "The tree may be PARTIALLY MIGRATED despite a passed docs gate — review "
            ".wavefoundry/logs/ and resolve before treating this upgrade as complete."
        )


def _docs_gate_summary_line(failed_phase: str | None) -> str:
    """Render the 'Docs gate:' summary value from real lock state (wave 1p44o).

    Replaces a previously hardcoded ``PASSED`` constant. ``failed_phase`` is the
    failure marker read from the upgrade lock:

    - ``None``       → the upgrade reached cleanup without a recorded failure → PASSED.
    - ``"docs_gate"`` → the docs gate itself failed → FAILED.
    - any other phase → the upgrade failed before the docs gate ran → NOT RUN.
    """
    if failed_phase is None:
        return "PASSED"
    if failed_phase == "docs_gate":
        return "FAILED"
    return f"NOT RUN (upgrade failed at phase: {failed_phase})"


def _is_major_or_minor_upgrade(from_version: str | None, to_version: str | None) -> bool:
    """True when ``from_version`` → ``to_version`` is a major or minor bump.

    Wave 1p5tk. Fully fail-safe: any unparseable/absent version returns False so
    the caller stays quiet rather than recommending on noise. Never raises.
    """
    if not from_version or not to_version:
        return False
    try:
        from check_version import _to_version

        old = _to_version(from_version)
        new = _to_version(to_version)
    except Exception:
        return False
    # major or minor changed (patch-only bumps and downgrades are excluded).
    return new[:2] != old[:2] and new > old


def _config_review_recommendation_lines(
    from_version: str | None, to_version: str | None
) -> list[str]:
    """Recommendation to evaluate the Framework Config Review on a major/minor upgrade.

    Wave 1p5tk. Stateless (no marker/threshold) — surfaced on every major/minor
    upgrade; the owner decides each time. Recommend-only; never blocks the upgrade.
    Returns [] (silent) on patch upgrades or any parse failure.
    """
    try:
        if not _is_major_or_minor_upgrade(from_version, to_version):
            return []
        return [
            "",
            f"Config review recommended (major/minor upgrade {from_version} → {to_version}):",
            "  A senior/principal architect or engineer should evaluate whether to run the",
            "  Framework Config Review (docs/prompts/framework-config-review.prompt.md) to audit",
            "  and retire stale agent config. Optional, human-initiated — it does not block anything.",
        ]
    except Exception:
        return []


def _run_reconciliation_scan(root: Path | None) -> tuple[list[dict], list[dict]]:
    """Wave 1p8et / 1p8o5 — run the shipped retired-surface reconciliation scan over *root*.

    Returns ``(reconciliation, host_permission_flags)`` — two lists of
    ``{file, line, retired_surface, matched, suggested}`` dicts (report-only — the scan never mutates
    any file):

    * ``reconciliation`` — stale refs in editable repo docs/prompts/configs/scripts (the agent edits).
    * ``host_permission_flags`` — stale refs in host permission/allow-rule files the agent cannot
      self-edit under host auto-mode guards (flagged for the operator; wave 1p8o5).

    Fully fail-safe: returns ``([], [])`` when *root* is None or any import/scan error occurs, so a
    scanner fault never breaks the upgrade summary.
    """
    if root is None:
        return [], []
    try:
        import reconcile_scan

        reconciliation, host_perm = reconcile_scan.scan_repo_channels(root)
        return (
            [ref.as_dict() for ref in reconciliation],
            [ref.as_dict() for ref in host_perm],
        )
    except Exception:  # noqa: BLE001 — fail-safe: a scan fault must never break the upgrade
        return [], []


def _reconciliation_recommendation_lines(
    from_version: str | None,
    to_version: str | None,
    findings: list[dict] | None = None,
    host_permission_flags: list[dict] | None = None,
) -> list[str]:
    """Recommendation to reconcile local surfaces against changed/retired framework surfaces.

    Wave 1p7ww / 1p8et / 1p8kz. Runs on EVERY upgrade (operator direction — a patch or a same-version
    build-successor can change/retire a surface during testing); NOT gated to major/minor like its
    sibling ``_config_review_recommendation_lines``. The mechanical reconciliation (prune pack-removed files,
    re-render surfaces, re-heal the ``python`` symlink) is automatic in the upgrade phases; this
    surfaces the *local-surface* part agents must still judge: docs/configs/scripts in THIS repo that
    referenced a framework surface the bump changed or RETIRED.

    Wave 1p8et: when ``findings`` (from the shipped ``reconcile_scan`` helper) are supplied, this emits
    the ACTIONABLE ``file:line → suggested wf form`` list instead of the recommend-only prose — the
    scan replaces the prose. Report-only by default; never blocks. An empty findings list still emits
    the heading + a "no stale references found" line so the operator sees the scan ran. Returns []
    (silent) only on a parse failure.

    Wave 1p8o5: ``host_permission_flags`` (stale refs in host permission/allow-rule files the agent
    cannot self-edit) are emitted in a DISTINCT section so the operator — not the agent — makes those
    edits. They are never folded into the editable list above (seed-160 "flagged separately").
    """
    try:
        # Wave 1p8kz (operator direction): run on EVERY upgrade, not only major/minor. A patch — or a
        # same-version build-successor during testing — can change or RETIRE a surface, and the scan is
        # report-only + cheap + exclusion-aware, so there is no reason to skip it.
        lines = [
            "",
            f"Reconciliation scan ({from_version} → {to_version}) — report-only:",
            "  Local surfaces (docs, prompts, configs, scripts) that named a framework surface this",
            "  upgrade CHANGED or RETIRED — e.g. the 1.9.0 cutover retired the `.wavefoundry/bin/*`",
            "  wrappers in favor of the cross-OS `wf` dispatcher. Update each below; never auto-fixed.",
        ]
        if findings:
            for ref in findings:
                # Print the ACTUAL matched reference (ref['matched']) — the literal bin path or the
                # .py-join text — not an assumed `.wavefoundry/bin/<name>` form (wrong for joins).
                # Tolerate a missing 'matched' (fail-safe) by falling back to the retired name.
                matched = ref.get("matched") or f".wavefoundry/bin/{ref['retired_surface']}"
                lines.append(
                    f"    {ref['file']}:{ref['line']} ({matched}) → {ref['suggested']}"
                )
        else:
            lines.append("    No stale retired-surface references found in local surfaces.")
        # Wave 1p8o5 — host permission/allow-rule files: a SEPARATE operator-flag section. The agent
        # cannot self-edit these under host auto-mode guards; name each stale rule + the new wf form
        # and let the operator make the edit (seed-160). Only emit the section when there are hits.
        if host_permission_flags:
            lines.append("")
            lines.append(
                "  Host permission/allow-rule files (flag for the OPERATOR — agents cannot self-edit"
            )
            lines.append(
                "  these under host auto-mode guards). Name the stale rule + the new wf form:"
            )
            for ref in host_permission_flags:
                matched = ref.get("matched") or f".wavefoundry/bin/{ref['retired_surface']}"
                lines.append(
                    f"    {ref['file']}:{ref['line']} ({matched}) → {ref['suggested']}"
                )
        return lines
    except Exception:
        return []


def _build_upgrade_summary(
    from_version: str | None,
    to_version: str | None,
    zip_path: Path | None,
    pruned_count: int,
    ran_index_rebuild: bool,
    failed_phase: str | None,
    reconciliation: list[dict],
    host_permission_flags: list[dict] | None = None,
) -> dict:
    """Wave 1p8eu — assemble the operator summary ONCE as a dict.

    Both the human prose and the machine-readable sentinel line are rendered from this single dict so
    they cannot drift. Reuses ``_docs_gate_summary_line`` and ``_is_major_or_minor_upgrade`` (the
    computed values that agents previously regex-scraped from prose). ``reconciliation`` carries the
    1p8et scan findings in editable repo surfaces (``[]`` when the scan found nothing).

    Wave 1p8o5: ``host_permission_flags`` carries the DISTINCT host permission/allow-rule findings the
    agent cannot self-edit (operator must edit them). Additive — it never disturbs ``reconciliation``.
    """
    return {
        "from_version": from_version,
        "to_version": to_version,
        "zip_applied": zip_path.name if zip_path else None,
        "pruned_count": pruned_count,
        "docs_gate": _docs_gate_summary_line(failed_phase),
        "index_update": (
            "docs layer complete, code layer running in background"
            if ran_index_rebuild
            else "not run — call with --update-index after editing pass"
        ),
        "failed_phase": failed_phase,
        "is_major_or_minor": _is_major_or_minor_upgrade(from_version, to_version),
        "reconciliation": reconciliation,
        "host_permission_flags": host_permission_flags or [],
        # 1p8xl: pack-search locations skipped because they were unreadable (e.g. a TCC-sandboxed
        # ~/Downloads). Surfaced so the operator can acknowledge — and grant access + re-run if a
        # newer pack lives there. Empty when every location read cleanly.
        "skipped_scan_locations": list(_PACK_SCAN_SKIPPED),
    }


def _emit_summary_line(summary: dict) -> None:
    """Wave 1p8eu/1p8kz — emit the machine-readable summary sentinel (fail-safe).

    ``wf_upgrade_response`` parses this single line into ``data['summary']``. Rendered from the
    SAME ``_build_upgrade_summary`` dict everywhere (prose + sentinel + primary-phase emit) so they
    cannot drift."""
    try:
        _log(WAVE_UPGRADE_SUMMARY_SENTINEL + json.dumps(summary, ensure_ascii=False))
    except (TypeError, ValueError):
        pass


def _emit_primary_phase_summary(
    from_version: str | None,
    to_version: str | None,
    zip_path: Path | None,
    pruned_count: int,
    root: Path | None,
) -> None:
    """Wave 1p8kz — emit the structured summary sentinel at the end of the primary upgrade phase
    (phases 0–4, the default ``wf_upgrade()`` call) so agents get ``data['summary']`` — including
    the 1p8et reconciliation findings — without waiting for the separate ``--cleanup`` phase. The full
    human operator prose still prints only at cleanup (``phase_cleanup`` → ``_print_operator_summary``);
    this emits the sentinel only, to avoid duplicating the prose. Wave 1p8kz (operator direction): the
    reconciliation scan runs on EVERY upgrade — not only major/minor — since a patch or same-version
    build-successor can change/retire a surface during testing (the rendered surfaces it needs are in
    place by phase 1); fail-safe."""
    reconciliation, host_permission_flags = (
        _run_reconciliation_scan(root) if root is not None else ([], [])
    )
    summary = _build_upgrade_summary(
        from_version=from_version,
        to_version=to_version,
        zip_path=zip_path,
        pruned_count=pruned_count,
        ran_index_rebuild=True,  # the default --yes path runs phase 4 (index update) before this point
        failed_phase=None,
        reconciliation=reconciliation,
        host_permission_flags=host_permission_flags,
    )
    _emit_summary_line(summary)


def _print_operator_summary(
    from_version: str | None,
    to_version: str | None,
    zip_path: Path | None,
    pruned_count: int,
    ran_index_rebuild: bool,
    failed_phase: str | None = None,
    root: Path | None = None,
) -> None:
    # Wave 1p8et/1p8kz: run the shipped retired-surface reconciliation scan on EVERY upgrade (operator
    # direction — a patch or same-version build-successor can change/retire a surface too), report-only
    # + fail-safe. Wave 1p8eu: build the summary dict ONCE so the prose + machine-readable sentinel
    # cannot drift.
    if root is not None and not failed_phase:
        reconciliation, host_permission_flags = _run_reconciliation_scan(root)
    else:
        reconciliation, host_permission_flags = [], []
    summary = _build_upgrade_summary(
        from_version=from_version,
        to_version=to_version,
        zip_path=zip_path,
        pruned_count=pruned_count,
        ran_index_rebuild=ran_index_rebuild,
        failed_phase=failed_phase,
        reconciliation=reconciliation,
        host_permission_flags=host_permission_flags,
    )

    from_str = from_version or "(none)"
    to_str = to_version or "(unknown)"
    _log("")
    if failed_phase:
        _log(f"Upgrade INCOMPLETE — failed during phase: {failed_phase}")
    else:
        _log("Upgrade complete")
    _log("=" * 40)
    _log(f"Version:            {from_str} → {to_str}")
    if zip_path:
        _log(f"Zip applied:        {zip_path.name}")
        _log("Zip retained:       yes (gitignored per seed-050)")
    else:
        _log("Zip applied:        none (upgraded from current tree)")
    _log("Surfaces rendered:  hooks, MCP config, bin launchers, agent surfaces")
    _log(f"Files pruned:       {summary['pruned_count']}")
    _log(f"Docs gate:          {summary['docs_gate']}")
    _log(f"Index update:       {summary['index_update']}")
    if summary["skipped_scan_locations"]:
        _log("")
        _log("⚠  Pack-search locations SKIPPED (permission/sandbox — could not read):")
        for loc in summary["skipped_scan_locations"]:
            _log(f"   - {loc}")
        _log("   These were NOT searched for a newer pack. If a newer pack lives in one of them, grant")
        _log("   the host access to that folder and re-run; otherwise acknowledge and proceed.")
    _log("Dashboard:          lock removed; auto-reindex will trigger on lock removal")
    _log("MCP reload: call wf_reload_mcp() (or wf_upgrade cleanup) to load upgraded server code in-process")
    _log("")
    # Wave 1p5tk — on a major/minor upgrade, recommend (don't run) the Framework
    # Config Review for a senior/principal owner to evaluate. Stateless + fail-safe.
    # Wave 1p7ww / 1p8et — and run the local-surface reconciliation scan (same major/minor gate),
    # surfacing the actionable file:line → suggested wf form list (report-only).
    if not failed_phase:
        for line in _config_review_recommendation_lines(from_version, to_version):
            _log(line)
        for line in _reconciliation_recommendation_lines(
            from_version, to_version, reconciliation, host_permission_flags
        ):
            _log(line)
    # Wave 1p8eu/1p8kz — emit the summary machine-readably so wf_upgrade_response parses it into
    # data['summary'] (fail-safe). Rendered from the SAME dict as the prose above (one source).
    _emit_summary_line(summary)
    # Wave 1p454 — defer to seed-160 as the authoritative editing-pass checklist
    # (do NOT enumerate its step-8 backfills here — they drift); fix the journal
    # label; prepend a secrets-resolution step before the docs-gate re-run.
    _log("Next steps for agent editing pass:")
    _log("  See seed-160 for the full editing-pass sequence; key steps:")
    _log("  1. Drift detection (seed-160 step 6)")
    _log("  2. Journal reconciliation (seed-160 step 0 / Reconcile journals)")
    _log("  3. Spec gaps via seed-230 (seed-160 step 4 / 160 step 8)")
    _log("  4. Resolve any docs/scan-findings.json entries via seed-213 (security reviewer) before re-running the docs gate")
    _log("  5. Docs gate re-run after edits (wf_garden_docs → wf_validate_docs, or wf docs-lint)")
    _log("  6. Index update: wf upgrade --update-index")
    _log("  7. Cleanup lock after rebuild: wf upgrade --cleanup")
    _log("")


def _finalize_failed_upgrade(root: Path, tree_mutated: bool, current_phase: str) -> None:
    """Decide the upgrade lock's fate when an in-progress upgrade phase fails.

    Wave 1p44o data-safety contract:

    - ``tree_mutated`` True  → the tree is half-replaced (zip extracted and/or
      surfaces rendered/pruned). RETAIN the lock and stamp it with a failure
      marker (``failed_phase`` / ``failed_at``) so the dashboard watcher stays
      paused and ``--cleanup`` / resume can read the real state. Do NOT remove it.
    - ``tree_mutated`` False → failure happened before any tree mutation; remove
      the lock so a clean retry isn't blocked (pre-1p44o behavior preserved).

    Extracted from the ``except SystemExit:`` handler so the data-safety decision
    is unit-testable in isolation.
    """
    import upgrade_lib

    state = upgrade_lib.read_upgrade_lock(root) or {}
    restart_pending = bool(state.get("dashboard_restart_pending"))
    if tree_mutated or restart_pending:
        upgrade_lib.update_upgrade_lock(
            root,
            failed_phase=current_phase,
            failed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        if current_phase in {"review_status_projection", "docs_gate"}:
            recovery = (
                "Resolve the typed review-state or docs findings, then run "
                "--resume-after-gate. Index publication and cleanup remain "
                "blocked until that recovery succeeds."
            )
        else:
            recovery = (
                "Resolve the failure, then re-run the full upgrade to restore "
                "a clean state."
            )
        _err(
            f"Upgrade failed during phase '{current_phase}'. The upgrade lock "
            "has been RETAINED with a failure marker so dashboard restart intent "
            "and any partially replaced tree remain visible. Inspect "
            f".wavefoundry/upgrade-in-progress.json. {recovery}"
        )
    else:
        upgrade_lib.remove_upgrade_lock(root)


# ── Wave 1p44z — secrets policy materialization (pre-gate) ────────────────────

def _count_committers(root: Path) -> int:
    """Count unique committer emails (last 24 months; all-time fallback when the
    windowed count is 0). Returns 0 on any git failure (no repo / no git)."""
    def _count(extra: list[str]) -> int:
        try:
            r = subprocess_util.isolated_run(
                ["git", "log", "--format=%ae", *extra],
                cwd=str(root), capture_output=True, text=True, check=False,
            )
        except Exception:
            return 0
        if r.returncode != 0:
            return 0
        return len({e.strip() for e in r.stdout.splitlines() if e.strip()})

    n = _count(["--since=2 years ago"])
    return n if n else _count([])


def _committer_threshold(n: int) -> int:
    """Map committer count to false_positive_confirmations_required (0–1→1, 2–6→2, 7+→3)."""
    if n <= 1:
        return 1
    return 2 if n <= 6 else 3


def materialize_secrets_policy(root: Path) -> str:
    """Wave 1p44z — ensure the project's committer-derived secrets policy is in
    effect BEFORE the first upgrade docs gate, so a fresh project is never blocked
    by the framework default (`false_positive_confirmations_required = 2`).

    Creates ``docs/scan-rules.toml`` with a ``[policy]`` threshold mapped from the
    committer count ONLY when the file is absent; it never overwrites an existing
    file or value (operator settings win). Returns an operator-visible status line.
    """
    proj = root / "docs" / "scan-rules.toml"
    if proj.exists():
        return "scan-rules policy: docs/scan-rules.toml already present — left unchanged."
    n = _count_committers(root)
    threshold = _committer_threshold(n)
    content = (
        "# wavefoundry project scan rules\n"
        "# false_positive_confirmations_required: auto-detected from git committer "
        "count (last 24 months) at upgrade.\n"
        "# Override this value if your team size has changed, then delete this comment.\n"
        "# confirmation_valid_days: a false-positive confirmation counts only while it is "
        "this many days old (default 365; set 0 to disable expiry).\n"
        "#   Solo maintainers (single committer) may set 0 — yearly re-confirmation is a "
        "no-op when you are the only reviewer who can re-confirm.\n"
        "# Add project-specific [[rules]] entries below to extend the framework default ruleset.\n"
        "\n[policy]\n"
        f"false_positive_confirmations_required = {threshold}\n"
        "confirmation_valid_days = 365\n"
    )
    try:
        proj.parent.mkdir(parents=True, exist_ok=True)
        proj.write_text(content, encoding="utf-8")
    except OSError as exc:
        return f"scan-rules policy: could not materialize docs/scan-rules.toml: {exc}"
    return (
        f"scan-rules policy: detected {n} committer(s) → "
        f"false_positive_confirmations_required = {threshold} "
        "(materialized docs/scan-rules.toml before the gate)."
    )


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomically write ``data`` as JSON via same-directory temp + os.replace.

    Same-directory temp (not /tmp) so the rename never crosses devices; bounded
    retry on the replace for Windows sharing violations (WinError 5/32 — the
    1p9iw pattern). A crash before the replace leaves the original file intact.
    """
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if sys.platform == "win32":
            import time
            for attempt in range(5):
                try:
                    os.replace(tmp, path)
                    return
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.2 * (attempt + 1))
        else:
            os.replace(tmp, path)
    finally:
        # No-op after a successful replace (the temp name no longer exists);
        # cleans up a partial temp after a failed write or exhausted retry.
        tmp.unlink(missing_ok=True)


def materialize_lifecycle_policy(root: Path) -> str:
    """Provision the lifecycle-ID scheme-v2 policy in docs/workflow-config.json.

    Deterministic, idempotent, atomic — the code path behind both the install
    seed (fresh epoch + scattered offset) and the upgrade pipeline (v1→v2
    migration: epoch = rollout date, offset = scanned max + merge margin).
    Idempotence is keyed on ``scheme_version == "v2"`` presence, all-or-nothing:
    a partial prior write (no scheme_version) is re-attempted; a repo already
    v2 is never re-epoched or re-offset. Existing IDs are never rewritten.

    Read-modify-write: only the ``lifecycle_id_policy`` value is replaced;
    every other top-level key is preserved byte-for-byte. An unparseable
    existing file fails loudly with NO write — never replace a
    corrupt-but-recoverable operator file. (The materialize_secrets_policy
    precedent above supplies the phase shape only; it is create-only and does
    not need any of this.)
    """
    import lifecycle_id

    cfg = root / "docs" / "workflow-config.json"
    data: dict = {}
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"lifecycle policy: {cfg} exists but could not be parsed ({exc}); "
                "refusing to overwrite a corrupt-but-recoverable file — fix the JSON and re-run"
            ) from exc
        if not isinstance(data, dict):
            raise RuntimeError(
                f"lifecycle policy: {cfg} must contain a JSON object at the top level"
            )

    policy = data.get("lifecycle_id_policy")
    if not isinstance(policy, dict):
        policy = {}
    if policy.get("scheme_version") == "v2":
        return "lifecycle policy: scheme_version v2 already provisioned — left unchanged (idempotent)."

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    fields = lifecycle_id.compute_v2_policy_fields(root, now_utc, root.name)
    migrated = "project_seed" not in fields

    # Preserve operator/unknown keys inside the block; replace the
    # framework-owned descriptive keys that describe the retired v1 packing.
    new_policy = dict(policy)
    for stale_key in ("time_unit", "buckets_per_day"):
        new_policy.pop(stale_key, None)
    new_policy.update(fields)
    new_policy.setdefault("prefix_width", 5)
    new_policy["notes"] = (
        "Scheme v2 (provisioned at "
        f"{fields['epoch_utc']}): value = offset + days_since_epoch * 4096 + "
        "blake2s-hash entropy (12 deterministic bits of kind+slug), base36, "
        "minimum width 5, no modulo — past 36^5 (~40 yr) IDs widen gracefully "
        "to 6 chars, never wrap. Lex/value order == time order for existing "
        "and new IDs (offset clears all pre-provisioning values); within a "
        "single day, IDs order by hash entropy, not mint time. node_bits is "
        "reserved (0 = full 12-bit hash entropy); hour_offset is v1-only and "
        "ignored under v2. Do not hand-edit epoch_utc, offset, or "
        "scheme_version after provisioning — issued IDs depend on them."
    )
    data["lifecycle_id_policy"] = new_policy

    try:
        cfg.parent.mkdir(parents=True, exist_ok=True)  # brand-new repo may lack docs/
        _atomic_write_json(cfg, data)
    except OSError as exc:
        # Fail LOUD: a soft return here would report exit 0 while the repo
        # silently keeps minting v1 (idempotence re-attempts on the next run,
        # but the caller must know THIS run did not provision).
        raise RuntimeError(f"lifecycle policy: could not write {cfg}: {exc}") from exc
    mode = (
        f"migrated v1→v2 (offset = scanned max + {lifecycle_id.V1_MERGE_MARGIN} margin)"
        if migrated
        else "fresh install (scattered start band, 40-year horizon floor)"
    )
    message = (
        f"lifecycle policy: provisioned scheme v2 — epoch {fields['epoch_utc']}, "
        f"offset {fields['offset']}; {mode}."
    )
    # Sanity backstop (delivery red-team): a genuine v1 history tops out around
    # a few million; an anomalously large scanned max (e.g. a word-like filename
    # matching the prefix pattern) silently burns the 5-char horizon. Warn loudly
    # when fewer than ~5 years of 5-char space remain so the operator can rename
    # the offending artifact and re-provision before the offset is depended upon.
    five_years_of_values = 1826 * 4096  # 5 yr × 365.25 d × 4096/day
    if fields["offset"] > 36 ** 5 - five_years_of_values:
        max_token = lifecycle_id.encode_base36(
            lifecycle_id.scan_max_prefix_value(root) or 0
        ).rjust(5, "0")
        message += (
            f" WARNING: the provisioned offset leaves under ~5 years of 5-character ID "
            f"space (scanned max prefix `{max_token}`) — if that prefix belongs to a stray "
            "word-like filename rather than a real ID, rename it, delete the "
            "lifecycle_id_policy block, and re-run provisioning."
        )
    return message


# ── Main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Automated Wavefoundry framework upgrade.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root (default: current directory)",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Non-interactive mode: skip confirmation prompt",
    )
    parser.add_argument(
        "--update-index",
        action="store_true",
        dest="update_index",
        help="Run phase 4 as incremental update — re-embeds only changed files (auto-escalates to full when chunker/model version changed)",
    )
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        dest="rebuild_index",
        help="Run phase 4 as full rebuild — re-embeds every file from scratch (use when --update-index is insufficient)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Run phase 5 (cleanup) only — removes the upgrade lock and prints summary",
    )
    parser.add_argument(
        "--resume-after-gate",
        action="store_true",
        dest="resume_after_gate",
        help=(
            "Resume a review-projection/docs-gate-failed upgrade: rebuild current "
            "review-status projection, then re-run docs-gardener + docs-lint against "
            "the already-extracted tree (no extract/render/prune). Requires a retained "
            "lock whose failed_phase is 'review_status_projection' or 'docs_gate'."
        ),
    )
    parser.add_argument(
        "--resume-after-memory",
        action="store_true",
        dest="resume_after_memory",
        help=(
            "Resume the retained upgrade after bounded historical-memory "
            "extraction and agent validation; publishes the index only when "
            "the authoritative SQLite pending census is zero."
        ),
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        dest="dry_run",
        help=(
            "Print the upgrade plan and hook inventory without modifying anything on disk. "
            "Surfaces seed diffs, extension module source, and convention hook scripts "
            "for agent review before the real upgrade runs."
        ),
    )
    parser.add_argument(
        "--detect-zip",
        action="store_true",
        dest="detect_zip",
        help=(
            "Print the absolute path of the highest-semver `wavefoundry-*.zip` "
            "across all search paths (repo root, ~/, ~/.wavefoundry/, "
            "~/.wavefoundry/dist/, ~/Downloads/), then exit 0. Exit 1 with empty output if no "
            "matching zip is found. Use this instead of `ls -1` so the answer "
            "comes from the same semver comparator the upgrade itself uses — "
            "`ls -1` sorts lexicographically, which puts `1.3.9` after `1.3.30`."
        ),
    )
    parser.add_argument(
        "--list-zips",
        action="store_true",
        dest="list_zips",
        help=(
            "Print every matching `wavefoundry-*.zip` across all search paths, "
            "one per line, semver-sorted (highest first), with the selected-"
            "latest prefixed by `* `. Use this when you need to see everything "
            "available, not just the selected pack. Exits 0 even when no zips "
            "are found (prints nothing in that case)."
        ),
    )
    parser.add_argument(
        "--materialize-lifecycle-policy",
        action="store_true",
        dest="materialize_lifecycle_policy",
        help=(
            "Run ONLY the lifecycle-ID policy provisioning (Phase 2c) against "
            "--root and exit: computes and atomically writes the scheme-v2 "
            "epoch/offset into docs/workflow-config.json (fresh install → "
            "install-date epoch + deterministic scattered offset; existing v1 "
            "history → rollout-date epoch + offset above the scanned max). "
            "Idempotent — a repo already on v2 is left unchanged. This is the "
            "command the install and upgrade seeds call; agents must not "
            "hand-compute epochs or offsets."
        ),
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    # Ensure upgrade_lib is importable (same directory as this script)
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))

    # ── Agent-facing zip-discovery helpers ────────────────────────────────
    # Routed before any other phase so they short-circuit without spawning
    # the upgrade pipeline. Both produce stable, machine-readable output for
    # agents that previously fell back to `ls -1` (broken under lex sort).
    if args.materialize_lifecycle_policy:
        try:
            print(materialize_lifecycle_policy(root))
        except RuntimeError as exc:
            print(f"upgrade: error: {exc}", file=sys.stderr)
            return 1
        return 0
    if args.detect_zip:
        z = _find_latest_release_zip(root)
        if z is None:
            return 1
        print(str(z))
        return 0
    if args.list_zips:
        _print_all_release_zips(root)
        return 0

    import upgrade_lib

    # ── Dry-run ────────────────────────────────────────────────────────────
    if args.dry_run:
        return phase_dry_run(root)

    def _zip_from_lock(lock: dict | None) -> Path | None:
        """Resolve the zip used in the original upgrade from the lock file.

        Prefers the ``zip_path`` field recorded at lock-write time so that
        standalone --update-index and --cleanup use the same extension module
        as the original run, even if a new zip has since arrived in the repo root.
        Falls back to ``_find_zip`` for locks written before this field existed.
        """
        if lock:
            recorded = lock.get("zip_path")
            if recorded:
                p = Path(recorded)
                if p.exists():
                    return p
        return _find_zip(root)

    def _memory_gate(lock: dict | None) -> tuple[object | None, str | None, dict | None]:
        if not isinstance(lock, dict):
            return None, None, None
        run_id = str(lock.get("memory_backfill_run_id") or "").strip()
        if not run_id:
            return None, None, None
        import memory_backfill

        return memory_backfill, run_id, memory_backfill.run_summary(root, run_id)

    def _unrecovered_review_or_docs_gate(lock: dict | None) -> bool:
        """Refuse every publication/cleanup path while a typed gate is failed."""

        failed_phase = (
            lock.get("failed_phase") if isinstance(lock, dict) else None
        )
        if failed_phase not in {"review_status_projection", "docs_gate"}:
            return False
        _err(
            "Index publication and cleanup are refused while the retained "
            f"upgrade lock has failed_phase={failed_phase!r}. Resolve the typed "
            "review-state or docs findings, run --resume-after-gate, then retry "
            "the requested phase."
        )
        return True

    def _new_code_upgrade_backstop(
        lock: dict | None,
    ) -> tuple[object | None, str | None, dict | None, int | None]:
        """Materialize migrations that a pre-upgrade runner could not know.

        The parent process may have loaded an older ``upgrade_wavefoundry``
        before extracting this release.  Its next ``--update-index`` or
        ``--cleanup`` invocation does run this newly installed module, so this
        is the mandatory fail-closed boundary before index publication.
        """

        if not isinstance(lock, dict):
            return None, None, None, None
        try:
            projection_counts = phase_review_status_projection(root)
        except SystemExit as exc:
            message = str(exc)
            upgrade_lib.update_upgrade_lock(
                root,
                failed_phase="review_status_projection",
                review_status_projection_failure=message,
            )
            _err(
                "Review-state migration requires operator action before index "
                f"publication: {message}. Resolve the typed review evidence, "
                "then run --resume-after-gate."
            )
            return None, None, None, 1
        import memory_backfill

        try:
            run_id = str(lock.get("memory_backfill_run_id") or "").strip()
            if not run_id:
                run_id = memory_backfill.ensure_run(root, "upgrade")
            summary = memory_backfill.sync_inventory(root, run_id)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            upgrade_lib.update_upgrade_lock(
                root,
                failed_phase="historical_memory_backfill",
                memory_backfill_last_failure=message,
            )
            _err(
                "Historical-memory migration could not establish durable state; "
                f"index publication is refused: {message}"
            )
            return None, None, None, memory_backfill.ACTION_REQUIRED_EXIT
        upgrade_lib.update_upgrade_lock(
            root,
            review_status_projection=projection_counts,
            memory_backfill_run_id=run_id,
            memory_backfill_state=summary["state"],
            memory_backfill_pending=(
                summary["remaining_waves"]
                + summary["candidates_pending"]
                + summary["failures"]
            ),
            memory_backfill_last_failure=summary["last_failure"],
        )
        return memory_backfill, run_id, summary, None

    # ── Standalone --resume-after-memory ──────────────────────────────────
    if getattr(args, "resume_after_memory", False):
        _open_log(root, mode="a")
        try:
            lock = upgrade_lib.read_upgrade_lock(root)
            if _unrecovered_review_or_docs_gate(lock):
                return 1
            backfill, run_id, summary = _memory_gate(lock)
            if backfill is None or run_id is None or summary is None:
                _err("No retained upgrade memory gate was found — nothing to resume.")
                return 1
            summary = backfill.sync_inventory(root, run_id)
            summary = backfill.reconcile_index_publication(root, run_id)
            if summary["state"] == "indexed":
                _log("Historical memory index publication is already complete.")
                return 0
            if summary["state"] != "ready_for_index":
                _err(
                    json.dumps(summary, sort_keys=True)
                    + "\nHistorical memory remains awaiting validation. Run "
                    "`wf memory-backfill --entry-path upgrade`, validate the "
                    "candidates, then retry --resume-after-memory."
                )
                return backfill.ACTION_REQUIRED_EXIT
            try:
                publication_pending = int(summary.get("candidates_drafted") or 0) > 0
                if publication_pending:
                    with backfill.index_publication_scope(run_id):
                        phase_index_update(root)
                    backfill.complete_index_publication(root, run_id)
                else:
                    phase_index_update(root)
                    backfill.mark_indexed(root, run_id)
            except Exception as exc:
                recovered = backfill.reconcile_index_publication(root, run_id)
                upgrade_lib.update_upgrade_lock(
                    root,
                    failed_phase="index_update",
                    memory_backfill_state=recovered["state"],
                    memory_backfill_last_failure=f"{type(exc).__name__}: {exc}",
                )
                _err(f"Historical memory index publication failed: {exc}")
                return (
                    backfill.ACTION_REQUIRED_EXIT
                    if recovered["state"] == "awaiting_validation"
                    else 1
                )
            upgrade_lib.update_upgrade_lock(
                root,
                memory_backfill_state="indexed",
                index_rebuilt_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
            _log("Historical memory validated; Phase 4 index publication complete.")
            return 0
        finally:
            _close_log()

    # Index/cleanup verbs cannot bypass an active historical-memory gate.
    if args.update_index or args.rebuild_index or args.cleanup:
        lock = upgrade_lib.read_upgrade_lock(root)
        if _unrecovered_review_or_docs_gate(lock):
            return 1
        backfill, _run_id, summary, gate_error = _new_code_upgrade_backstop(lock)
        if gate_error is not None:
            return gate_error
        if (
            backfill is not None
            and summary is not None
            and summary["state"] != "indexed"
        ):
            _err(
                "Historical memory validation is pending; index/cleanup is refused. "
                "Run bounded memory backfill + validation, then --resume-after-memory."
            )
            return backfill.ACTION_REQUIRED_EXIT

    # ── Standalone --update-index ──────────────────────────────────────────────
    if args.update_index:
        _open_log(root, mode="a")
        try:
            lock = upgrade_lib.read_upgrade_lock(root)
            _rb_from = lock.get("from_version") if lock else None
            _rb_to = lock.get("to_version") if lock else None
            _rb_zip = _zip_from_lock(lock)
            _rb_ctx = UpgradeContext(root, _rb_from, _rb_to, _rb_zip, args.yes)
            _rb_ext = _load_extension_module(_rb_zip)
            _run_hook("pre_index_update", _rb_ctx, _rb_ext)
            # Wave 1p3dk / 1p3ho: always call phase_index_update — the indexer's
            # internal auto-escalate handles the chunker/walker bump full-rebuild
            # case. Trust the indexer; no explicit force-rebuild routing.
            phase_index_update(root)
            # Wave 1ryce: lifecycle scheme-v2 provisioning backstop from NEW code. An MCP wf_upgrade
            # from a version BEFORE 1.10.1 runs the pre-upgrade orchestrator through preflight (which
            # therefore has no Phase 2c) and the old server may never reach the phase_cleanup backstop —
            # so the repo silently stays on v1 IDs. This `--update-index` subprocess runs the freshly
            # extracted (NEW) code and is invoked by every MCP upgrade flow post-extract, so it is the
            # reliable new-code place to heal. Idempotent (a repo already on scheme_version v2 is a no-op)
            # and fail-safe (a config error degrades to a recovery pointer — never fails the index phase).
            _ensure_lifecycle_policy_backstop(root)
            # Wave 1rych: bootstrap-file removal from NEW code, mirroring the lifecycle backstop above.
            # `_remove_root_bootstrap_file` is also called in the extract phase (Phase 0b), but on a
            # from-old MCP upgrade the extract runs the OLD in-process orchestrator (which predates the
            # removal helper), so the stray root `install-wavefoundry.md` is left behind. This
            # `--update-index` subprocess runs the freshly extracted (NEW) code and is invoked by every
            # MCP upgrade flow post-extract, so it reliably cleans up the file even from an older source
            # version. Idempotent (a missing file is a no-op) and fail-safe (never aborts the index phase).
            _remove_root_bootstrap_file(root)
            _run_hook("post_index_update", _rb_ctx, _rb_ext)
            upgrade_lib.update_upgrade_lock(
                root,
                index_rebuilt_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
        finally:
            _close_log()
        return 0

    # ── Standalone --rebuild-index ─────────────────────────────────────────────
    if args.rebuild_index:
        _open_log(root, mode="a")
        try:
            lock = upgrade_lib.read_upgrade_lock(root)
            _rb_from = lock.get("from_version") if lock else None
            _rb_to = lock.get("to_version") if lock else None
            _rb_zip = _zip_from_lock(lock)
            _rb_ctx = UpgradeContext(root, _rb_from, _rb_to, _rb_zip, args.yes)
            _rb_ext = _load_extension_module(_rb_zip)
            _run_hook("pre_index_rebuild", _rb_ctx, _rb_ext)
            phase_index_rebuild(root)
            _run_hook("post_index_rebuild", _rb_ctx, _rb_ext)
            upgrade_lib.update_upgrade_lock(
                root,
                index_rebuilt_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
        finally:
            _close_log()
        return 0

    # ── Standalone --cleanup ───────────────────────────────────────────────
    if args.cleanup:
        _open_log(root, mode="a")
        try:
            lock = upgrade_lib.read_upgrade_lock(root)
            # Wave 1p44o — distinguish "no lock" (warn, don't print a phantom
            # summary) from a real or failed lock, and surface the failure phase.
            _cl_present = lock is not None
            _cl_from = lock.get("from_version") if lock else None
            _cl_to = lock.get("to_version") if lock else None
            _cl_zip = _zip_from_lock(lock)
            _cl_pruned = (lock.get("pruned_count") or 0) if lock else 0
            # True when --rebuild-index already ran and recorded its completion.
            _cl_rebuilt = bool(lock.get("index_rebuilt_at")) if lock else False
            _cl_failed = lock.get("failed_phase") if lock else None
            _cl_ctx = UpgradeContext(root, _cl_from, _cl_to, _cl_zip, args.yes)
            _cl_ext = _load_extension_module(_cl_zip)
            _run_hook("pre_cleanup", _cl_ctx, _cl_ext)
            phase_cleanup(
                root=root,
                from_version=_cl_from,
                to_version=_cl_to,
                zip_path=_cl_zip,
                pruned_count=_cl_pruned,
                ran_index_rebuild=_cl_rebuilt,
                failed_phase=_cl_failed,
                lock_present=_cl_present,
            )
            _run_hook("post_cleanup", _cl_ctx, _cl_ext)
        finally:
            _close_log()
        return 0

    # ── Standalone --resume-after-gate (waves 1p44r / 1t3dm) ──────────────
    if getattr(args, "resume_after_gate", False):
        _open_log(root, mode="a")
        try:
            lock = upgrade_lib.read_upgrade_lock(root)
            if lock is None:
                _err("No upgrade lock found — nothing to resume.")
                return 1
            failed_phase = lock.get("failed_phase") if isinstance(lock, dict) else None
            resumable_gate_phases = {"review_status_projection", "docs_gate"}
            if failed_phase not in resumable_gate_phases:
                _err(
                    "Resume-after-gate requires a retained lock whose failed_phase is "
                    "'review_status_projection' or 'docs_gate'; found "
                    f"failed_phase={failed_phase!r}. Resolve the upgrade manually "
                    "or re-run the full upgrade."
                )
                return 1
            _log(
                "\n── Resume: rebuilding review state and re-running the docs "
                "gate against the already-extracted tree ──"
            )
            try:
                # The ledger or required-lane set may have changed while the
                # upgrade was paused. Rebuild the projection on EVERY retry
                # before docs lint; a prior lock marker is evidence only, not a
                # substitute for this current-authority read.
                projection_counts = phase_review_status_projection(root)
            except SystemExit:
                upgrade_lib.update_upgrade_lock(
                    root,
                    failed_phase="review_status_projection",
                    failed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
                _err(
                    "Review-state projection still requires action — lock retained "
                    "(failed_phase=review_status_projection); resolve the typed "
                    "review evidence and run --resume-after-gate again."
                )
                _close_log()
                raise
            upgrade_lib.update_upgrade_lock(
                root, review_status_projection=projection_counts
            )
            try:
                # Re-run only the current-authority projection plus
                # docs-gardener/docs-lint; no extract/render/prune.
                phase_docs_gate(root)
            except SystemExit:
                upgrade_lib.update_upgrade_lock(
                    root,
                    failed_phase="docs_gate",
                    failed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
                _err(
                    "Docs gate still failing — lock retained "
                    "(failed_phase=docs_gate); resolve the findings and run "
                    "--resume-after-gate again."
                )
                _close_log()
                raise
            # Gate passed — clear the failure marker so downstreams (dashboard,
            # --cleanup) see a clean (non-failed) lock again.
            upgrade_lib.update_upgrade_lock(root, failed_phase=None, failed_at=None)
            _log(
                "  Review-state projection and docs gate PASSED on resume — "
                "failure marker cleared. Run --update-index then --cleanup to "
                "finish the upgrade."
            )
        finally:
            _close_log()
        return 0

    # ── Full upgrade: phases 0–3 ───────────────────────────────────────────
    _log(f"\nWavefoundry Upgrade — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    _log(f"Repository root: {root}")

    # Phase 0 — Pre-flight
    from_version, to_version, zip_path = phase_preflight(root, yes=args.yes)

    # Build context and load extension module from zip (before extraction).
    ctx = UpgradeContext(root, from_version, to_version, zip_path, args.yes)
    ext_mod = _load_extension_module(zip_path)

    _run_hook("post_preflight", ctx, ext_mod)

    # Save old MANIFEST before zip extraction overwrites it
    old_manifest = root / ".wavefoundry" / "framework" / "MANIFEST"
    if old_manifest.exists():
        try:
            shutil.copy2(old_manifest, OLD_MANIFEST_TMP)
            _log(f"  Saved old MANIFEST to {OLD_MANIFEST_TMP}")
        except OSError as exc:
            _log(f"  ⚠  Could not save old MANIFEST: {exc}")

    # Write upgrade lock (zip_path recorded so --rebuild-index / --cleanup can
    # reload the same extension module without guessing from the current repo state).
    upgrade_lib.write_upgrade_lock(
        root,
        from_version=from_version,
        to_version=to_version or "unknown",
        zip_path=zip_path,
    )
    _log("  Upgrade lock written — dashboard will pause indexing.")

    # Open the upgrade log and tell the operator where to watch it.
    _open_log(root, mode="w")
    log_path = upgrade_log_path(root)
    _log(f"  Upgrade log: {log_path}")
    _log(f"  Watch:       tail -f {log_path}")

    # Wave 1p44o — data-safety: track whether the tree has been mutated (zip
    # extracted / surfaces rendered / files pruned) and which phase is running,
    # so the except SystemExit handler can RETAIN the lock with a failure marker
    # on a post-mutation failure instead of tearing the guard down on a
    # half-replaced tree.
    tree_mutated = False
    current_phase = "init"

    try:
        # Packaged upgrades execute the new pre-extract migration from the zip.
        # A current-tree upgrade has no extension module, so run that same
        # shipped migration directly before any framework mutation.
        if zip_path is None:
            current_phase = "runtime_lock_cutover"
            import upgrade_extensions

            upgrade_extensions.pre_extract(ctx)

        # Wave 1p3dk / 1p3ho: snapshot the consumer's pre-existing framework
        # version constants BEFORE extract so we can log any transitions in
        # the upgrade output. The transitions themselves are operator-visible
        # signals; the indexer's `build_index` auto-escalate handles
        # chunker/walker rebuilds and the graph layer rebuilds on first query
        # when GRAPH_BUILDER_VERSION advances. We log, then trust.
        ctx.pre_extract_chunker_versions = _snapshot_pre_extract_chunker_versions(root)
        _pre_extract_all_versions = _snapshot_pre_extract_versions(root)

        # Apply zip if found
        if zip_path:
            current_phase = "extract"
            _run_hook("pre_extract", ctx, ext_mod)
            # Wave 1p44r — extract idempotence: if the on-disk framework already
            # equals to_version, do NOT destructively re-extract (e.g. when retrying
            # preflight_to_docs_gate after a docs-gate failure on an at-target tree).
            if _tree_already_at(root, to_version):
                _log(
                    f"\n── Phase 0b: Tree already at {to_version} — "
                    "skipping re-extract (idempotent) ──"
                )
            else:
                _log(f"\n── Phase 0b: Applying zip {zip_path.name} ──")
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(str(root))
                # Tree is now half-replaced — from here a failure must RETAIN the
                # lock (wave 1p44o) rather than remove it.
                tree_mutated = True
                _log(f"  Extracted {zip_path.name}")
            _run_hook("post_extract", ctx, ext_mod)

            # Wave 1rxyi: the zip drops the single-use bootstrap `install-wavefoundry.md` at the project
            # root (it ships at the zip root by design). Prune is MANIFEST-scoped to .wavefoundry/ and
            # never removes a root file, so clean it up here — fail-safe, so it never aborts the upgrade.
            _remove_root_bootstrap_file(root)

            # Note any framework version transitions in the upgrade log.
            # Don't branch on them — Phase 4 always runs phase_index_update at
            # the end, and the indexer's auto-escalate routes to full rebuild
            # when needed. The log is the operator-visible signal that the
            # rebuild will be substantial rather than incremental.
            _transitions = _detect_version_transitions(_pre_extract_all_versions, root)
            if _transitions:
                _log("\n⚠  Framework version transitions detected:")
                for _name, _old, _new in _transitions:
                    _log(f"   {_name}: {_old} → {_new}")
                _log(
                    "   Phase 4 will run a full re-embed where the semantic "
                    "versions changed (indexer auto-escalate); the graph layer "
                    "is re-extracted in Phase 4b during THIS upgrade when "
                    "GRAPH_BUILDER_VERSION advanced (graph-only, fresh "
                    "subprocess). Reload MCP (wf_reload_mcp) or restart the "
                    "host after the upgrade so a running server does not keep "
                    "the old graph extractor."
                )
                # Track for compat with v1 tests + post-condition path.
                _chunker_transition = next(
                    ((o, n) for nm, o, n in _transitions if nm.startswith("CHUNKER_VERSION")),
                    None,
                )
                if _chunker_transition is not None:
                    ctx.chunker_version_bumped = True
                    ctx.chunker_version_transition = _chunker_transition
            else:
                # 1p5do: no transitions detected — surface the rebuild signal when there was no
                # baseline to compare against (otherwise this stays silent exactly when it matters).
                _warn_if_no_version_baseline(_pre_extract_all_versions, root)

        # Phase 1
        current_phase = "surface_rendering"
        _run_hook("pre_surface_rendering", ctx, ext_mod)
        phase_surface_rendering(root)
        # Surface rendering mutates the tree even when no zip was applied
        # (upgrade-from-current-tree path) — mark mutated here too.
        tree_mutated = True
        _run_hook("post_surface_rendering", ctx, ext_mod)

        # Wave 1p44p follow-up — stamp framework_revision now that VERSION is
        # extracted and the manifest is rendered, so the installed-revision marker
        # tracks the pack instead of freezing at the pre-upgrade value.
        if _stamp_manifest_revision(root):
            _log(f"  Installed revision: stamped framework_revision = {_read_pack_version(root)}")

        # Phase 2
        current_phase = "pruning"
        _run_hook("pre_pruning", ctx, ext_mod)
        pruned_count = phase_pruning(root)
        # Old MANIFEST was only needed for pruning — remove it now.
        try:
            OLD_MANIFEST_TMP.unlink(missing_ok=True)
        except OSError:
            pass
        # Persist the prune count so --cleanup can report it accurately.
        upgrade_lib.update_upgrade_lock(root, pruned_count=pruned_count)
        _run_hook("post_pruning", ctx, ext_mod)

        # Phase 2b — Wave 1p44z: materialize the committer-derived secrets policy
        # BEFORE the first docs gate (which runs the secrets scan), so a fresh
        # project is never blocked by the framework-default confirmation threshold.
        current_phase = "policy_materialization"
        _log("\n── Phase 2b: Secrets policy ──")
        _log(f"  {materialize_secrets_policy(root)}")

        # Phase 2c — provision/migrate the lifecycle-ID scheme-v2 policy
        # (epoch = rollout date, offset clears scanned history). Idempotent:
        # a repo already on v2 is left unchanged. RuntimeError (corrupt config /
        # failed atomic write) converts to SystemExit so the pipeline's failure
        # handler records failed_phase in the retained lock and closes the log
        # instead of leaking a raw traceback.
        current_phase = "lifecycle_policy_materialization"
        _log("\n── Phase 2c: Lifecycle-ID policy ──")
        try:
            _log(f"  {materialize_lifecycle_policy(root)}")
        except RuntimeError as exc:
            _err(f"  ERROR: {exc}")
            raise SystemExit(1)

        current_phase = "review_status_projection"
        projection_counts = phase_review_status_projection(root)
        upgrade_lib.update_upgrade_lock(
            root, review_status_projection=projection_counts
        )
        _log(
            "\n── Phase 2d: Review-state projection ──\n  "
            + json.dumps(projection_counts, sort_keys=True)
        )

        # Phase 3
        current_phase = "docs_gate"
        _run_hook("pre_docs_gate", ctx, ext_mod)
        phase_docs_gate(root)
        _run_hook("post_docs_gate", ctx, ext_mod)

        # Historical memory is reconciled by the newly extracted implementation
        # before index publication.  The retained upgrade lock mirrors only the
        # run id/current gate; memory-state.sqlite owns the authoritative work.
        current_phase = "awaiting_memory_validation"
        import memory_backfill

        memory_run_id = memory_backfill.ensure_run(root, "upgrade")
        memory_summary = memory_backfill.sync_inventory(root, memory_run_id)
        memory_summary = memory_backfill.reconcile_index_publication(
            root, memory_run_id
        )
        upgrade_lib.update_upgrade_lock(
            root,
            memory_backfill_run_id=memory_run_id,
            memory_backfill_state=memory_summary["state"],
            memory_backfill_pending=(
                memory_summary["remaining_waves"]
                + memory_summary["candidates_pending"]
                + memory_summary["failures"]
            ),
            memory_backfill_last_failure=memory_summary["last_failure"],
        )
        if memory_summary["state"] == "awaiting_validation":
            _log(
                "\nHistorical memory requires bounded extraction and agent validation "
                "before Phase 4.\n"
                + json.dumps(memory_summary, sort_keys=True)
                + "\nReload MCP, run memory_backfill(mode='create', "
                "entry_path='upgrade') and memory_validate, then call "
                "wf_upgrade(phase='resume_after_memory')."
            )
            _close_log()
            return memory_backfill.ACTION_REQUIRED_EXIT
        # Phase 4 — Wave 1p3dk / 1p3ho: always run index update at the end of
        # upgrade so operators don't have to remember a separate
        # `--update-index` invocation. The indexer's `build_index`
        # auto-escalate handles both cases (chunker/walker bumped → full
        # rebuild; otherwise → incremental). Trust the indexer to do whatever
        # it needs; the version-transition log in Phase 0b already signals to
        # the operator what to expect.
        current_phase = "index_update"
        _run_hook("pre_index_update", ctx, ext_mod)
        publication_pending = (
            int(memory_summary.get("candidates_drafted") or 0) > 0
            and memory_summary["state"] == "ready_for_index"
        )
        if publication_pending:
            with memory_backfill.index_publication_scope(memory_run_id):
                phase_index_update(root)
        else:
            phase_index_update(root)
        if publication_pending:
            memory_backfill.complete_index_publication(root, memory_run_id)
        _run_hook("post_index_update", ctx, ext_mod)
        upgrade_lib.update_upgrade_lock(
            root,
            memory_backfill_state="indexed",
            index_rebuilt_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    except SystemExit:
        # A phase or hook failed (phase_docs_gate raises sys.exit(1) on a docs
        # gate failure; hooks may sys.exit too). Clean up the temp manifest in
        # case pruning hadn't reached it yet.
        try:
            OLD_MANIFEST_TMP.unlink(missing_ok=True)
        except OSError:
            pass
        # Wave 1p44o — retain the lock with a failure marker on a post-mutation
        # failure (half-replaced tree); remove it only on a pre-mutation failure.
        _finalize_failed_upgrade(root, tree_mutated, current_phase)
        _close_log()
        raise

    # Wave 1p8kz — emit the structured summary sentinel now (end of the default primary phase) so the
    # wf_upgrade() call returns data['summary'] WITH the 1p8et reconciliation findings, instead of
    # only on the separate --cleanup phase (where the agent often isn't looking). Full operator prose
    # still prints at cleanup.
    _emit_primary_phase_summary(from_version, to_version, zip_path, pruned_count, root)

    _log(
        "\n✓ Phases 0–4 complete. Proceed with agent editing pass, then run:\n"
        "    upgrade-wavefoundry --cleanup\n"
        "\n(Re-run upgrade-wavefoundry --update-index manually only if you edit "
        "additional files post-upgrade and want the index refreshed.)"
    )
    _close_log()

    return 0


if __name__ == "__main__":
    sys.exit(main())

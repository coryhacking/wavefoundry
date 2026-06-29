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
# UTF-8. Reconfigure at import so EVERY entry into this module (CLI, `wf upgrade`, MCP `wave_upgrade`
# which re-execs this script) prints non-ASCII without raising on a cp1252 console.
cli_stdio.configure_utf8_stdio()

# Wave 1p8gv: `/tmp` does not exist on native Windows — the old fallback raised FileNotFoundError when
# copying the pre-upgrade MANIFEST. `tempfile.gettempdir()` resolves the correct OS temp dir (honors
# TMPDIR/TEMP/TMP) cross-platform.
OLD_MANIFEST_TMP = Path(tempfile.gettempdir()) / "wf-manifest-old.txt"

UPGRADE_LOG_FILENAME = "upgrade.log"

# Wave 1p8eu: the operator summary is built ONCE as a dict and emitted machine-readably on a single
# line prefixed with this sentinel (alongside the human prose). ``server_impl.wave_upgrade_response``
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
    """Return the shared tool-venv Python when present, else the current interpreter.

    Builds the path via the single resolver (wave 1p7pl); semantics unchanged.
    """
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
    # Wave 1p64x: dashboard metadata now lives in the server lock file (one sidecar).
    meta = root / ".wavefoundry" / "dashboard-server.lock"
    if not meta.exists():
        return False, None, None
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
        pid = data.get("pid")
        url = data.get("url")
        if isinstance(pid, int) and pid > 0:
            # Wave 1p654 (review follow-up): harden the liveness check to match the
            # lifecycle tools — a bare os.kill(pid, 0) accepts a zombie or a recycled
            # PID. Verify the recorded PID is actually a live dashboard for THIS root
            # via the shared cmdline scan; fall back to os.kill when the scan is
            # unavailable (Windows / ps error) so behavior is unchanged there.
            try:
                import dashboard_lib
                live = dashboard_lib.dashboard_cmdline_pids(root)
            except Exception:  # noqa: BLE001 — best-effort; fall back to os.kill
                live = None
            if live is not None and pid not in live:
                return False, None, None
            try:
                os.kill(pid, 0)
                return True, pid, url
            except (ProcessLookupError, OSError):
                pass
    except (OSError, json.JSONDecodeError):
        pass
    return False, None, None


import re as _re

_ZIP_NAME_RE = _re.compile(r"^wavefoundry-(\d+\.\d+\.\d+)\.([A-Za-z0-9]+)\.zip$")
_HOME_DIR = Path("~")
_HOME_WAVEFOUNDRY_DIR = Path("~/.wavefoundry")
_DIST_DIR = Path("~/.wavefoundry/dist")
_DOWNLOADS_DIR = Path("~/Downloads")  # 1p5dk: browser-downloaded packs commonly land here


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
    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        for entry in search_dir.iterdir():
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
        if not search_dir.is_dir():
            continue
        for entry in search_dir.iterdir():
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
# mismatches via full rebuild; the graph layer rebuilds on first query when
# `GRAPH_BUILDER_VERSION` advances. This module's job is to surface those
# transitions in the upgrade log so operators see what changed, then trust the
# indexer / graph layer to do the right thing on the next call.

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


# Backwards-compatible name (1p3ho v1 callers; kept for the existing test surface).
def _snapshot_pre_extract_chunker_versions(root: Path) -> dict[str, str]:
    """Read the consumer's pre-existing index meta.json and return its
    chunker_versions mapping. Handles both modern per-layer dict and legacy
    scalar `chunker_version` key. Empty dict when meta.json absent or unreadable."""
    meta_path = root / ".wavefoundry" / "index" / "meta.json"
    if not meta_path.is_file():
        return {}
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
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


def _snapshot_pre_extract_versions(root: Path) -> dict[str, str]:
    """Snapshot all relevant framework version constants from the consumer's
    pre-existing index/graph state files. Returns a flat dict with keys
    `chunker_docs`, `chunker_code`, `walker`, `graph_builder` (any subset
    when the corresponding state isn't present)."""
    out: dict[str, str] = {}
    # Chunker + walker live in .wavefoundry/index/meta.json
    chunker_versions = _snapshot_pre_extract_chunker_versions(root)
    if "docs" in chunker_versions:
        out["chunker_docs"] = chunker_versions["docs"]
    if "code" in chunker_versions:
        out["chunker_code"] = chunker_versions["code"]
    meta_path = root / ".wavefoundry" / "index" / "meta.json"
    if meta_path.is_file():
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            walker = data.get("walker_version")
            if isinstance(walker, (str, int)) and str(walker).strip():
                out["walker"] = str(walker)
        except (OSError, ValueError):
            pass
    # Graph builder version lives in the framework graph state
    graph_state = root / ".wavefoundry" / "framework" / "index" / "graph" / "framework-graph-state.json"
    if graph_state.is_file():
        try:
            data = json.loads(graph_state.read_text(encoding="utf-8"))
            gb = data.get("builder_version")
            if isinstance(gb, (str, int)) and str(gb).strip():
                out["graph_builder"] = str(gb)
        except (OSError, ValueError):
            pass
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
    meta_path = root / ".wavefoundry" / "index" / "meta.json"
    if not meta_path.is_file():
        return True
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
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
    hook_path = ctx.root / ".wavefoundry" / "hooks" / script_name
    if hook_path.exists() and os.access(str(hook_path), os.X_OK):
        env = {
            **os.environ,
            "WF_FROM_VERSION": ctx.from_version or "",
            "WF_TO_VERSION": ctx.to_version or "",
            "WF_ROOT": str(ctx.root),
            "WF_YES": "1" if ctx.yes else "0",
        }
        try:
            result = subprocess_util.isolated_run(
                [str(hook_path)], env=env, cwd=str(ctx.root),
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
            _log("⚠  Stale upgrade lock detected (PID not running) — clearing it.")
            upgrade_lib.remove_upgrade_lock(root)
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
    result = subprocess_util.isolated_run(
        [_preferred_python(), str(setup_script), "--root", str(root)],
        cwd=str(root),
        check=False,
    )
    if result.returncode != 0:
        _log(f"  ⚠  Docs index update exited {result.returncode} — continuing.")

    # Phase 4b: update the GRAPH index too (blocking; graph-only is fast, ~seconds,
    # no embedding). Symmetric with the semantic update: `--graph-only` (no --full)
    # is an UPDATE that auto-escalates to a full re-extract when GRAPH_BUILDER_VERSION
    # advanced (graph_indexer's version check) — so a graph-builder bump materializes
    # during the upgrade instead of waiting for the first-query lazy rebuild.
    _log("  Phase 4b: updating graph index (blocking) ...")
    graph_result = subprocess_util.isolated_run(
        [_preferred_python(), str(setup_script), "--root", str(root), "--graph-only"],
        cwd=str(root),
        check=False,
    )
    if graph_result.returncode != 0:
        _log(f"  ⚠  Graph index update exited {graph_result.returncode} — continuing (first-query rebuild remains the safety net).")

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
            env=subprocess_util.utf8_child_env(),  # 1p8gv: UTF-8 stdio in the child (cp1252 safety)
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

    upgrade_lib.remove_upgrade_lock(root)
    if failed_phase:
        _log(
            f"  Upgrade lock removed — it carried a failure marker (phase: "
            f"{failed_phase}); the tree may be half-replaced. Re-run the upgrade "
            "to restore a clean state."
        )
    else:
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
    if not failed_phase:
        _regenerate_codebase_map_on_upgrade(root)

    _print_operator_summary(
        from_version=from_version,
        to_version=to_version,
        zip_path=zip_path,
        pruned_count=pruned_count,
        ran_index_rebuild=ran_index_rebuild,
        failed_phase=failed_phase,
        root=root,
    )


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
    import json as _json
    try:
        meta = _json.loads((root / ".wavefoundry" / "index" / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
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
            "then run: wave_index_build(content='code', mode='rebuild')"
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
    }


def _emit_summary_line(summary: dict) -> None:
    """Wave 1p8eu/1p8kz — emit the machine-readable summary sentinel (fail-safe).

    ``wave_upgrade_response`` parses this single line into ``data['summary']``. Rendered from the
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
    (phases 0–4, the default ``wave_upgrade()`` call) so agents get ``data['summary']`` — including
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
    _log("Dashboard:          lock removed; auto-reindex will trigger on lock removal")
    _log("MCP reload: call wave_mcp_reload() (or wave_upgrade cleanup) to load upgraded server code in-process")
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
    # Wave 1p8eu/1p8kz — emit the summary machine-readably so wave_upgrade_response parses it into
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
    _log("  5. Docs gate re-run after edits (wave_garden → wave_validate, or wf docs-lint)")
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

    if tree_mutated:
        upgrade_lib.update_upgrade_lock(
            root,
            failed_phase=current_phase,
            failed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        _err(
            f"Upgrade failed during phase '{current_phase}' after the tree was "
            "modified. The upgrade lock has been RETAINED with a failure marker "
            "so the dashboard stays paused and the half-replaced tree is not "
            "reindexed. Inspect .wavefoundry/upgrade-in-progress.json, resolve "
            "the failure, then re-run the upgrade or run --cleanup to acknowledge."
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
            "Resume a docs-gate-failed upgrade: re-run ONLY docs-gardener + docs-lint "
            "against the already-extracted tree (no extract/render/prune). Requires a "
            "retained lock whose failed_phase is 'docs_gate' (wave 1p44r)."
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
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    # Ensure upgrade_lib is importable (same directory as this script)
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))

    # ── Agent-facing zip-discovery helpers ────────────────────────────────
    # Routed before any other phase so they short-circuit without spawning
    # the upgrade pipeline. Both produce stable, machine-readable output for
    # agents that previously fell back to `ls -1` (broken under lex sort).
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

    # ── Standalone --resume-after-gate (wave 1p44r) ────────────────────────
    if getattr(args, "resume_after_gate", False):
        _open_log(root, mode="a")
        try:
            lock = upgrade_lib.read_upgrade_lock(root)
            if lock is None:
                _err("No upgrade lock found — nothing to resume.")
                return 1
            failed_phase = lock.get("failed_phase") if isinstance(lock, dict) else None
            if failed_phase != "docs_gate":
                _err(
                    "Resume-after-gate requires a retained lock whose failed_phase is "
                    f"'docs_gate'; found failed_phase={failed_phase!r}. Resolve the "
                    "upgrade manually or re-run the full upgrade."
                )
                return 1
            _log("\n── Resume: re-running docs gate against the already-extracted tree ──")
            try:
                # Re-run ONLY docs-gardener + docs-lint; no extract/render/prune.
                phase_docs_gate(root)
            except SystemExit:
                # Refresh failed_at so the retained lock reflects the LATEST
                # attempt (forensics); failed_phase stays 'docs_gate' (delivery
                # review nit).
                upgrade_lib.update_upgrade_lock(
                    root, failed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
                _err(
                    "Docs gate still failing — lock retained (failed_phase=docs_gate); "
                    "resolve the findings and run --resume-after-gate again."
                )
                _close_log()
                raise  # propagate sys.exit(1) — non-zero exit on repeated failure
            # Gate passed — clear the failure marker so downstreams (dashboard,
            # --cleanup) see a clean (non-failed) lock again.
            upgrade_lib.update_upgrade_lock(root, failed_phase=None, failed_at=None)
            _log(
                "  Docs gate PASSED on resume — failure marker cleared. Run "
                "--update-index then --cleanup to finish the upgrade."
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
                    "   Phase 4 will run a full re-embed where versions "
                    "changed (indexer auto-escalate); graph layer rebuilds "
                    "on its next query."
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

        # Phase 3
        current_phase = "docs_gate"
        _run_hook("pre_docs_gate", ctx, ext_mod)
        phase_docs_gate(root)
        _run_hook("post_docs_gate", ctx, ext_mod)

        # Phase 4 — Wave 1p3dk / 1p3ho: always run index update at the end of
        # upgrade so operators don't have to remember a separate
        # `--update-index` invocation. The indexer's `build_index`
        # auto-escalate handles both cases (chunker/walker bumped → full
        # rebuild; otherwise → incremental). Trust the indexer to do whatever
        # it needs; the version-transition log in Phase 0b already signals to
        # the operator what to expect.
        current_phase = "index_update"
        _run_hook("pre_index_update", ctx, ext_mod)
        phase_index_update(root)
        _run_hook("post_index_update", ctx, ext_mod)
        upgrade_lib.update_upgrade_lock(
            root,
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
    # wave_upgrade() call returns data['summary'] WITH the 1p8et reconciliation findings, instead of
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

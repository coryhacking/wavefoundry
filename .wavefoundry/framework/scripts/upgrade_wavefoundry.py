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
import subprocess
import sys
import types
import zipfile
from pathlib import Path

# ── Resolve paths ─────────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent
FRAMEWORK_DIR = SCRIPTS_DIR.parent
BIN_DIR = FRAMEWORK_DIR / "bin"

OLD_MANIFEST_TMP = Path(
    os.environ.get("TMPDIR", "/tmp")
) / "wf-manifest-old.txt"

UPGRADE_LOG_FILENAME = "upgrade.log"


def upgrade_log_path(root: Path) -> Path:
    return root / ".wavefoundry" / "logs" / UPGRADE_LOG_FILENAME


def _tool_venv_base() -> Path:
    """Return the configured shared Wavefoundry tool-venv base path."""
    return Path(os.environ.get("WAVEFOUNDRY_TOOL_VENV", "~/.wavefoundry/venv")).expanduser()


def _preferred_python() -> str:
    """Return the shared tool-venv Python when present, else the current interpreter."""
    venv_python = _tool_venv_base() / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(venv_python) if venv_python.exists() else sys.executable


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
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            _log_file.write(f"[{ts}] {msg}\n")
        except OSError:
            pass


def _err(msg: str) -> None:
    full = f"ERROR: {msg}"
    print(full, file=sys.stderr, flush=True)
    if _log_file is not None:
        try:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            _log_file.write(f"[{ts}] {full}\n")
        except OSError:
            pass


def _detect_dashboard(root: Path) -> tuple[bool, int | None, str | None]:
    """Return (running, pid, url) for the local dashboard."""
    meta = root / ".wavefoundry" / "dashboard-server.json"
    if not meta.exists():
        return False, None, None
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
        pid = data.get("pid")
        url = data.get("url")
        if isinstance(pid, int) and pid > 0:
            # Quick liveness check
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


def _find_latest_release_zip(root: Path) -> Path | None:
    """Return the highest-semver wavefoundry zip across the supported search paths.

    Search locations:
      1. repository root
      2. ~/
      3. ~/.wavefoundry/
      4. ~/.wavefoundry/dist/

    Non-matching filenames are skipped silently. When multiple zips share the
    same MAJOR.MINOR.PATCH, the one with the lexicographically greatest
    4-character build suffix is returned.
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
            key = (v, build)
            if best is None or key > best:
                best = key
                best_path = entry
    return best_path


def _find_zip(root: Path) -> Path | None:
    """Return the best available wavefoundry zip, or None.

    Search order:
      1. highest semver zip across repo root, ~/, ~/.wavefoundry/, and ~/.wavefoundry/dist/
    """
    return _find_latest_release_zip(root)


def _read_pack_version(root: Path) -> str | None:
    p = root / ".wavefoundry" / "framework" / "VERSION"
    try:
        return p.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _read_installed_revision(root: Path) -> str | None:
    p = root / ".wavefoundry" / "framework" / "MANIFEST"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return str(data.get("framework_revision", "")).strip() or None
    except (OSError, json.JSONDecodeError):
        return None


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
    ) -> None:
        self.root = root
        self.from_version = from_version
        self.to_version = to_version
        self.zip_path = zip_path
        self.yes = yes

    def __repr__(self) -> str:
        return (
            f"UpgradeContext(from={self.from_version!r}, to={self.to_version!r}, "
            f"root={str(self.root)!r})"
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
            result = subprocess.run(
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
    return subprocess.run(cmd, cwd=str(root), check=check)


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
    _log("Docs gate:          .wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint")
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
    script = SCRIPTS_DIR / "render_platform_surfaces.py"
    if not script.exists():
        _log("  render_platform_surfaces.py not found — skipping surface rendering.")
        return
    result = subprocess.run(
        [_preferred_python(), str(script), "--repo-root", str(root)],
        cwd=str(root),
        check=False,
    )
    if result.returncode != 0:
        _err("Surface rendering failed.")
        sys.exit(2)
    _log("  Surfaces rendered.")


# ── Phase 2 — Pruning ─────────────────────────────────────────────────────────

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
    result = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, check=False)
    if result.stdout:
        _log(result.stdout.rstrip())
    if result.returncode != 0:
        _log(f"  Pruning exited {result.returncode} — continuing (non-fatal).")
        return 0
    # Count pruned lines heuristically
    pruned = sum(1 for line in result.stdout.splitlines() if "removed" in line.lower() or "pruned" in line.lower())
    _log(f"  Pruning complete.")
    return pruned


# ── Phase 3 — Docs gate ───────────────────────────────────────────────────────

def phase_docs_gate(root: Path) -> None:
    _log("\n── Phase 3: Docs gate ──")
    gardener = root / ".wavefoundry" / "bin" / "docs-gardener"
    linter = root / ".wavefoundry" / "bin" / "docs-lint"

    for label, script in [("docs-gardener", gardener), ("docs-lint", linter)]:
        if script.exists():
            cmd: list[str] = [str(script)]
        else:
            # Fallback to Python script directly
            py_name = label.replace("-", "_") + ".py"
            py_script = SCRIPTS_DIR / py_name
            if py_script.exists():
                cmd = [_preferred_python(), str(py_script)]
            else:
                _log(f"  {label} not found — skipping.")
                continue

        result = subprocess.run(cmd, cwd=str(root), check=False)
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
    result = subprocess.run(
        [_preferred_python(), str(setup_script), "--root", str(root)],
        cwd=str(root),
        check=False,
    )
    if result.returncode != 0:
        _log(f"  ⚠  Docs index update exited {result.returncode} — continuing.")

    _log("  Phase 4b: launching code index update in background ...")
    background_cmd = [
        _preferred_python(), str(setup_script),
        "--root", str(root),
        "--background-code",
    ]
    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
        "cwd": str(root),
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(background_cmd, **kwargs)
    _log("  Code index update running in background.")


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
    result = subprocess.run(
        [_preferred_python(), str(setup_script), "--root", str(root), "--full"],
        cwd=str(root),
        check=False,
    )
    if result.returncode != 0:
        _log(f"  ⚠  Docs index rebuild exited {result.returncode} — continuing.")

    _log("  Phase 4b: launching code index rebuild in background ...")
    background_cmd = [
        _preferred_python(), str(setup_script),
        "--root", str(root),
        "--background-code",
        "--full",
    ]
    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
        "cwd": str(root),
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(background_cmd, **kwargs)
    _log("  Code index rebuild running in background.")


# ── Phase 5 — Cleanup & summary ───────────────────────────────────────────────

def phase_cleanup(
    root: Path,
    from_version: str | None,
    to_version: str | None,
    zip_path: Path | None,
    pruned_count: int,
    ran_index_rebuild: bool,
) -> None:
    import upgrade_lib

    _log("\n── Phase 5: Cleanup ──")
    upgrade_lib.remove_upgrade_lock(root)
    _log("  Upgrade lock removed — dashboard will trigger post-upgrade reindex.")

    _print_operator_summary(
        from_version=from_version,
        to_version=to_version,
        zip_path=zip_path,
        pruned_count=pruned_count,
        ran_index_rebuild=ran_index_rebuild,
    )


def _print_operator_summary(
    from_version: str | None,
    to_version: str | None,
    zip_path: Path | None,
    pruned_count: int,
    ran_index_rebuild: bool,
) -> None:
    from_str = from_version or "(none)"
    to_str = to_version or "(unknown)"
    _log("")
    _log("Upgrade complete")
    _log("=" * 40)
    _log(f"Version:            {from_str} → {to_str}")
    if zip_path:
        _log(f"Zip applied:        {zip_path.name}")
        _log("Zip retained:       yes (gitignored per seed-050)")
    else:
        _log("Zip applied:        none (upgraded from current tree)")
    _log("Surfaces rendered:  hooks, MCP config, bin launchers, agent surfaces")
    _log(f"Files pruned:       {pruned_count}")
    _log("Docs gate:          PASSED")
    if ran_index_rebuild:
        _log("Index update:       docs layer complete, code layer running in background")
    else:
        _log("Index update:       not run — call with --update-index after editing pass")
    _log("Dashboard:          lock removed; auto-reindex will trigger on lock removal")
    _log("MCP reload: call wave_mcp_reload() (or wave_upgrade cleanup) to load upgraded server code in-process")
    _log("")
    _log("Next steps for agent editing pass:")
    _log("  1. Drift detection (seed-160 step 6)")
    _log("  2. Journal reconciliation (seed-160 step 0e)")
    _log("  3. Spec gaps via seed-230 (seed-160 step 4 / 160 step 8)")
    _log("  4. Docs gate re-run after edits (wave_garden → wave_validate, or bin/docs-lint)")
    _log("  5. Index update: upgrade-wavefoundry --update-index")
    _log("  6. Cleanup lock after rebuild: upgrade-wavefoundry --cleanup")
    _log("")


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
        "--dry-run", "-n",
        action="store_true",
        dest="dry_run",
        help=(
            "Print the upgrade plan and hook inventory without modifying anything on disk. "
            "Surfaces seed diffs, extension module source, and convention hook scripts "
            "for agent review before the real upgrade runs."
        ),
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    # Ensure upgrade_lib is importable (same directory as this script)
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))

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
            _cl_from = lock.get("from_version") if lock else None
            _cl_to = lock.get("to_version") if lock else None
            _cl_zip = _zip_from_lock(lock)
            _cl_pruned = (lock.get("pruned_count") or 0) if lock else 0
            # True when --rebuild-index already ran and recorded its completion.
            _cl_rebuilt = bool(lock.get("index_rebuilt_at")) if lock else False
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
            )
            _run_hook("post_cleanup", _cl_ctx, _cl_ext)
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

    try:
        # Apply zip if found
        if zip_path:
            _run_hook("pre_extract", ctx, ext_mod)
            _log(f"\n── Phase 0b: Applying zip {zip_path.name} ──")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(str(root))
            _log(f"  Extracted {zip_path.name}")
            _run_hook("post_extract", ctx, ext_mod)

        # Phase 1
        _run_hook("pre_surface_rendering", ctx, ext_mod)
        phase_surface_rendering(root)
        _run_hook("post_surface_rendering", ctx, ext_mod)

        # Phase 2
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

        # Phase 3
        _run_hook("pre_docs_gate", ctx, ext_mod)
        phase_docs_gate(root)
        _run_hook("post_docs_gate", ctx, ext_mod)

    except SystemExit:
        # A phase or hook failed — remove lock before exiting.
        # Also clean up the temp manifest in case pruning hadn't reached it yet.
        try:
            OLD_MANIFEST_TMP.unlink(missing_ok=True)
        except OSError:
            pass
        upgrade_lib.remove_upgrade_lock(root)
        _close_log()
        raise

    _log(
        "\n✓ Phases 0–3 complete. Proceed with agent editing pass, then run:\n"
        "    upgrade-wavefoundry --update-index\n"
        "    upgrade-wavefoundry --cleanup\n"
        "\nOr to update and clean in one step:\n"
        "    upgrade-wavefoundry --update-index && upgrade-wavefoundry --cleanup"
    )
    _close_log()

    return 0


if __name__ == "__main__":
    sys.exit(main())

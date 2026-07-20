"""Framework-side upgrade extension hooks.

This module is loaded directly from inside the upgrade zip by
``upgrade_wavefoundry.py`` *before* extraction, so hooks fire at the right
phase boundaries without requiring a pre-existing copy on disk.

Hook functions
--------------
Define any of the functions below.  Each receives an ``UpgradeContext``
and should return ``None`` on success.  Raising any exception (or calling
``sys.exit()``) aborts the upgrade with exit code 3.

Available hooks (in call order):

    post_preflight(ctx)         after pre-flight checks, before zip extraction
    pre_extract(ctx)            immediately before zip extraction
    post_extract(ctx)           immediately after zip extraction
    pre_surface_rendering(ctx)  before render_platform_surfaces.py
    post_surface_rendering(ctx) after  render_platform_surfaces.py
    pre_pruning(ctx)            before prune_framework.py
    post_pruning(ctx)           after  prune_framework.py
    pre_docs_gate(ctx)          before docs-gardener && docs-lint
    post_docs_gate(ctx)         after  docs-gardener && docs-lint
    pre_index_update(ctx)       before setup_index.py (--update-index path, incremental)
    post_index_update(ctx)      after  setup_index.py (--update-index path)
    pre_index_rebuild(ctx)      before setup_index.py (--rebuild-index path, full)
    post_index_rebuild(ctx)     after  setup_index.py (--rebuild-index path)
    pre_cleanup(ctx)            before lock removal and operator summary
    post_cleanup(ctx)           after  lock removal and operator summary

UpgradeContext attributes
-------------------------
    ctx.root          Path  — repository root
    ctx.from_version  str | None — installed revision before upgrade
    ctx.to_version    str | None — target version from zip or pack
    ctx.zip_path      Path | None — path to the zip being applied
    ctx.yes           bool — True when running non-interactively (--yes / MCP)

Version-gated example
---------------------
    def post_pruning(ctx):
        # Only needed when upgrading from before the config schema change.
        if ctx.from_version and ctx.from_version >= "2026-06-01a":
            return
        _migrate_workflow_config(ctx.root)

Convention hooks
----------------
Project operators can also place executable scripts at:

    .wavefoundry/hooks/<hook-name-with-dashes>

e.g. ``.wavefoundry/hooks/post-surface-rendering``

They receive the same version info via environment variables:

    WF_FROM_VERSION   installed revision (empty string if unknown)
    WF_TO_VERSION     target version (empty string if unknown)
    WF_ROOT           absolute path to the repository root
    WF_YES            "1" if non-interactive, "0" otherwise

Convention hooks run after the extension module hook for the same phase.

Security note
-------------
The extension module is loaded from the zip by ``exec()``-ing its source into a
fresh ``types.ModuleType`` before any files are extracted.  It runs with the
operator's full user privileges — treat the zip as trusted input and verify its
provenance before running the upgrade.  The ``--dry-run`` flag surfaces the
extension module source and all convention hook scripts for review before any
disk writes occur.
"""
from __future__ import annotations

import json
import importlib.util
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


_LEGACY_RUNTIME_LOCKS = (
    ("review-evidence-adoptions.lock", 0),
    ("dashboard-start.lock", 1 << 30),
    ("dashboard-server.lock", 1 << 30),
)


def _read_json_object(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _update_upgrade_state(root: Path, **fields) -> None:
    path = root / ".wavefoundry" / "upgrade-in-progress.json"
    data = _read_json_object(path)
    if not path.exists():
        raise RuntimeError("upgrade-in-progress.json is missing during lock cutover")
    data.update(fields)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _legacy_lock_is_held(path: Path, offset: int) -> bool:
    """Probe a pre-cutover lock without importing not-yet-extracted code."""

    if not path.exists():
        return False
    handle = path.open("r+b")
    acquired = False
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(offset)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                return True
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (BlockingIOError, OSError):
                return True
        acquired = True
        return False
    finally:
        if acquired:
            try:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(offset)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()
        else:
            handle.close()


def _stop_dashboard_for_lock_cutover(root: Path) -> tuple[bool, int | None]:
    """Stop the old-path dashboard through the installed lifecycle implementation."""

    meta_paths = (
        root / ".wavefoundry" / "locks" / "dashboard-server.lock",
        root / ".wavefoundry" / "dashboard-server.lock",
    )
    meta = next(
        (_read_json_object(path) for path in meta_paths if path.exists()),
        {},
    )
    port = meta.get("port")
    restart_port = port if isinstance(port, int) and port > 0 else None
    scripts = root / ".wavefoundry" / "framework" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        import server_impl

        response = server_impl.wf_stop_dashboard_response(root)
    except Exception as exc:
        raise RuntimeError(f"unable to stop dashboard before lock cutover: {exc}") from exc
    if response.get("status") != "ok":
        raise RuntimeError("dashboard stop failed before runtime-lock cutover")
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    stopped = bool(data.get("stopped"))
    already_stopped = bool(data.get("already_stopped"))
    if not (stopped or already_stopped):
        raise RuntimeError("dashboard could not be verified stopped before lock cutover")
    return stopped, restart_port


def _cut_over_runtime_locks(root: Path) -> None:
    """Perform the one-way old-path cleanup before new runtime code is extracted."""

    was_running, restart_port = _stop_dashboard_for_lock_cutover(root)
    _update_upgrade_state(
        root,
        dashboard_restart_pending=was_running,
        dashboard_restart_port=restart_port,
        runtime_lock_cutover_complete=False,
    )
    old_root = root / ".wavefoundry"
    held = [
        name
        for name, offset in _LEGACY_RUNTIME_LOCKS
        if _legacy_lock_is_held(old_root / name, offset)
    ]
    legacy_producers = old_root / "logs" / "context-efficiency-producers"
    legacy_producer_leases = (
        list(legacy_producers.glob("*.lock"))
        if legacy_producers.exists()
        else []
    )
    producer_held = [
        lease.name
        for lease in legacy_producer_leases
        if _legacy_lock_is_held(lease, 0)
    ]
    if held:
        raise RuntimeError(
            "old runtime lock still held; quiesce/reload lifecycle writers before upgrade: "
            + ", ".join(held)
        )
    if producer_held:
        raise RuntimeError(
            "old context-efficiency producer lease is still held; reload active agents before upgrade: "
            + ", ".join(producer_held)
        )
    # The migration is deliberately check-then-delete: no old carrier is
    # removed until every carrier has been proven unlocked.
    for name, _offset in _LEGACY_RUNTIME_LOCKS:
        try:
            (old_root / name).unlink()
        except FileNotFoundError:
            pass
    if legacy_producers.exists():
        for lease in legacy_producer_leases:
            lease.unlink(missing_ok=True)
        try:
            legacy_producers.rmdir()
        except OSError:
            pass
    _update_upgrade_state(root, runtime_lock_cutover_complete=True)


def pre_extract(ctx):
    """Quiesce old dedicated lock carriers before installing canonical-only paths."""

    _cut_over_runtime_locks(ctx.root)


def _installed_memory_backfill(root: Path):
    """Load the just-extracted coordinator, even under a pre-upgrade runner."""

    scripts = root / ".wavefoundry" / "framework" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import memory_backfill

    return memory_backfill


def _installed_upgrade_module(root: Path):
    """Load the just-extracted upgrader without reusing the old runner module."""

    scripts = root / ".wavefoundry" / "framework" / "scripts"
    path = scripts / "upgrade_wavefoundry.py"
    if not path.is_file():
        raise RuntimeError(f"newly extracted upgrader is missing: {path}")
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location(
        "_wavefoundry_installed_upgrade_projection",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load newly extracted upgrader: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pre_docs_gate(ctx):
    """Project review state before a newly extracted validator can enforce it.

    A pre-upgrade runner has already loaded its old ``upgrade_wavefoundry``
    module, but it executes this extension from the new archive.  Loading the
    installed module by file path avoids the old ``sys.modules`` entry and gives
    that runner the new one-way projection migration before docs-lint runs.
    """

    lock = _read_json_object(
        ctx.root / ".wavefoundry" / "upgrade-in-progress.json"
    )
    if "review_status_projection" in lock:
        return
    installed = _installed_upgrade_module(ctx.root)
    counts = installed.phase_review_status_projection(ctx.root)
    _update_upgrade_state(ctx.root, review_status_projection=counts)


def post_docs_gate(ctx):
    """Bootstrap the memory pause under both old and new upgrade runners."""

    backfill = _installed_memory_backfill(ctx.root)
    run_id = backfill.ensure_run(ctx.root, "upgrade")
    summary = backfill.sync_inventory(ctx.root, run_id)
    _update_upgrade_state(
        ctx.root,
        memory_backfill_run_id=run_id,
        memory_backfill_state=summary["state"],
        memory_backfill_pending=(
            summary["remaining_waves"]
            + summary["candidates_pending"]
            + summary["failures"]
        ),
        memory_backfill_last_failure=summary["last_failure"],
    )
    if summary["state"] == "awaiting_validation":
        print(
            "\nHistorical memory requires bounded extraction and agent validation "
            "before index publication.\n"
            + json.dumps(summary, sort_keys=True)
            + "\nReload MCP, inspect wf_upgrade_status(), run "
            "memory_backfill(mode='create', entry_path='upgrade') and "
            "memory_validate for each validation_worklist item, then call "
            "wf_upgrade(phase='resume_after_memory').",
            flush=True,
        )
        raise SystemExit(backfill.ACTION_REQUIRED_EXIT)


def pre_index_update(ctx):
    """Keep candidate publication on the newly installed runner."""

    lock = _read_json_object(
        ctx.root / ".wavefoundry" / "upgrade-in-progress.json"
    )
    run_id = str(lock.get("memory_backfill_run_id") or "").strip()
    if not run_id:
        return
    backfill = _installed_memory_backfill(ctx.root)
    summary = backfill.reconcile_index_publication(ctx.root, run_id)
    if summary["state"] == "awaiting_validation":
        raise SystemExit(backfill.ACTION_REQUIRED_EXIT)
    if (
        summary["state"] == "ready_for_index"
        and int(summary.get("candidates_drafted") or 0) > 0
    ):
        print(
            "\nHistorical memory is ready for receipt-owned publication. "
            "Reload the installed MCP/runtime and call "
            "wf_upgrade(phase='resume_after_memory').",
            flush=True,
        )
        raise SystemExit(backfill.ACTION_REQUIRED_EXIT)
    _update_upgrade_state(
        ctx.root,
        memory_backfill_state=summary["state"],
        memory_backfill_pending=(
            summary["remaining_waves"]
            + summary["candidates_pending"]
            + summary["failures"]
        ),
    )


def post_index_update(ctx):
    """Seal an old runner's zero-candidate/no-source historical run."""

    lock = _read_json_object(
        ctx.root / ".wavefoundry" / "upgrade-in-progress.json"
    )
    run_id = str(lock.get("memory_backfill_run_id") or "").strip()
    if not run_id:
        return
    backfill = _installed_memory_backfill(ctx.root)
    summary = backfill.reconcile_index_publication(ctx.root, run_id)
    if (
        summary["state"] == "ready_for_index"
        and int(summary.get("candidates_drafted") or 0) == 0
    ):
        backfill.mark_indexed(ctx.root, run_id)
        summary = backfill.run_summary(ctx.root, run_id)
    if summary["state"] != "indexed":
        raise RuntimeError(
            "candidate-bearing historical-memory publication requires the "
            "newly installed resume_after_memory runner"
        )
    _update_upgrade_state(ctx.root, memory_backfill_state="indexed")

# ---------------------------------------------------------------------------
# 1.4.x → 1.5.0 migration (wave 1p35d / 1p3ay)
# ---------------------------------------------------------------------------
#
# Wave 1p35d introduced three changes that break in-place on existing consumer
# installs running ``Upgrade wave framework`` from 1.4.x:
#
#   1. C4 (1p35l): docs-lint enforces ``Role:`` on every ``docs/agents/*.md``.
#      Custom agent docs added by operators after their last install fail lint
#      on the first post-upgrade docs gate run.
#
#   2. C5 (1p35n): ``.claude/hooks/pycache-cleanup*`` launcher files become
#      orphans — the framework no longer renders them but they remain in
#      consumer repos.
#
#   3. C5 (1p35n): ``.claude/settings.json`` ``PostToolUse`` Bash hook row
#      pointing at the retired ``pycache-cleanup`` launcher persists because
#      ``render_platform_surfaces.py`` merges settings rather than overwriting.
#      Claude Code invokes a deleted launcher on every Bash tool call.
#
# Each migration below is idempotent: re-running ``Upgrade wave framework``
# performs zero work after the migrations have already run. Version-gated by
# ``_from_version_predates(from_version, "1.5.0")``; from 1.5.0 onward the
# migrations skip entirely.

_PRE_1_5_0_CUTOFF: tuple[int, int, int] = (1, 5, 0)

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def _parse_semver_prefix(version: str) -> tuple[int, int, int] | None:
    """Return (major, minor, patch) when ``version`` starts with a semver
    triple. Returns None for unparseable inputs (date-style or empty)."""
    if not version:
        return None
    match = _SEMVER_RE.match(version)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _from_version_predates(from_version: str | None, cutoff: str) -> bool:
    """True when ``from_version`` is older than ``cutoff`` (or unparseable).

    Unknown / unparseable inputs return True so we treat them as "old" — the
    migrations are idempotent, so re-running them on an already-migrated state
    is safe; missing a needed migration is not.
    """
    cutoff_parsed = _parse_semver_prefix(cutoff)
    if cutoff_parsed is None:
        return True
    parsed = _parse_semver_prefix(from_version or "")
    if parsed is None:
        return True
    return parsed < cutoff_parsed


# --- Migration 1: Role: backfill ---------------------------------------------

_AGENT_DOC_ROLE_EXEMPT_NAMES = frozenset({
    "README.md", "session-handoff.md", "platform-mapping.md",
})
_ROLE_LINE_RE = re.compile(r"^Role:\s+", re.MULTILINE)
_STATUS_LINE_RE = re.compile(r"^(Status:\s+.*)$", re.MULTILINE)
_OWNER_LINE_RE = re.compile(r"^(Owner:\s+.*)$", re.MULTILINE)


def _backfill_role_field_on_agent_docs(root: Path) -> list[str]:
    """Insert ``Role: <slug>`` into agent docs missing the field.

    Returns the list of repository-relative paths modified. Empty list when
    no modifications were needed.

    Walks ``docs/agents/*.md``, ``docs/agents/specialists/*.md``, and
    ``docs/agents/personas/*.md``. Skips:
    - Exempt filenames (README.md, session-handoff.md, platform-mapping.md)
    - Anything under ``docs/agents/journals/`` (journal docs)
    - Files that already declare ``Role:``

    Inserts ``Role: <stem>`` immediately after the ``Status:`` line, falling
    back to insertion after ``Owner:`` if no ``Status:`` line exists.
    """
    modified: list[str] = []
    agents_root = root / "docs" / "agents"
    if not agents_root.is_dir():
        return modified

    # Wave 1p3b9 (1p3b7 F6): recursive walk replaces the previous fixed-subdir
    # iteration so enterprise nested layouts (e.g.,
    # `docs/agents/teams/<team>/<role>.md`) are covered. `journals` at any
    # depth is skipped; the exempt-filename list still applies.
    try:
        candidates = sorted(agents_root.rglob("*.md"))
    except OSError:
        return modified
    for path in candidates:
        if not path.is_file():
            continue
        if path.name in _AGENT_DOC_ROLE_EXEMPT_NAMES:
            continue
        if "journals" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _ROLE_LINE_RE.search(text):
            continue  # already has Role:, no work needed
        stem = path.stem
        replacement = lambda m, s=stem: f"{m.group(1)}\nRole: {s}"
        new_text, count = _STATUS_LINE_RE.subn(replacement, text, count=1)
        if count == 0:
            new_text, count = _OWNER_LINE_RE.subn(replacement, text, count=1)
        if count == 0:
            # No anchor line — skip rather than corrupt the file
            continue
        try:
            path.write_text(new_text, encoding="utf-8")
        except OSError:
            continue
        try:
            modified.append(str(path.relative_to(root)).replace("\\", "/"))  # wave 1p9hm: forward-slash
        except ValueError:
            modified.append(str(path))
    return modified


# --- Migration 2: Pycache launcher cleanup -----------------------------------

_PYCACHE_LAUNCHER_NAMES = ("pycache-cleanup", "pycache-cleanup.py", "pycache-cleanup.cmd")


def _delete_pycache_hook_launchers(root: Path) -> list[str]:
    """Delete orphan ``.claude/hooks/pycache-cleanup*`` files.

    Returns the list of repository-relative paths deleted. Empty list when
    none existed.
    """
    deleted: list[str] = []
    hooks_dir = root / ".claude" / "hooks"
    if not hooks_dir.is_dir():
        return deleted
    for name in _PYCACHE_LAUNCHER_NAMES:
        path = hooks_dir / name
        if not path.exists():
            continue
        try:
            path.unlink()
        except OSError:
            continue
        try:
            deleted.append(str(path.relative_to(root)).replace("\\", "/"))  # wave 1p9hm: forward-slash
        except ValueError:
            deleted.append(str(path))
    return deleted


# --- Migration 3: settings.json pycache row strip ----------------------------


def _is_retired_pycache_row(entry) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("matcher") != "Bash":
        return False
    nested = entry.get("hooks")
    if not isinstance(nested, list) or not nested:
        return False
    first = nested[0]
    if not isinstance(first, dict):
        return False
    command = first.get("command")
    if not isinstance(command, str):
        return False
    normalized = command.lower().rstrip()
    return (normalized.endswith("pycache-cleanup")
            or normalized.endswith("pycache-cleanup.cmd"))


def _strip_pycache_row_from_settings_file(settings_path: Path, root: Path) -> str | None:
    """Strip the retired pycache row from a single settings.json-shaped file.

    Returns the repo-relative path when modified, else None. Used to handle
    both ``.claude/settings.json`` and the personal-override
    ``.claude/settings.local.json`` (wave 1p3b9 / 1p3b7 F4).
    """
    if not settings_path.is_file():
        return None
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    hooks_block = data.get("hooks")
    if not isinstance(hooks_block, dict):
        return None
    post_tool = hooks_block.get("PostToolUse")
    if not isinstance(post_tool, list):
        return None
    original_len = len(post_tool)
    post_tool_filtered = [e for e in post_tool if not _is_retired_pycache_row(e)]
    if len(post_tool_filtered) == original_len:
        return None
    hooks_block["PostToolUse"] = post_tool_filtered
    try:
        settings_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        return None
    try:
        return str(settings_path.relative_to(root)).replace("\\", "/")  # wave 1p9hm: forward-slash
    except ValueError:
        return str(settings_path)


def _strip_pycache_row_from_claude_settings(root: Path) -> list[str]:
    """Remove the retired ``PostToolUse`` Bash → pycache-cleanup hook row from
    both ``.claude/settings.json`` AND ``.claude/settings.local.json``.

    Returns a list of relative paths modified (possibly empty, one, or two
    entries). Preserves all other hook rows including operator-added customs.

    Wave 1p3b9 (1p3b7 F4): added the personal-override settings.local.json to
    the strip set so enterprise consumers with shared local-overrides don't
    leave the orphan row behind. The original 1p35d C7 migration only touched
    the committed `settings.json`.

    Matches a hook block whose ``matcher == "Bash"`` AND whose nested
    ``hooks[0].command`` ends with ``pycache-cleanup`` or
    ``pycache-cleanup.cmd``. Does not touch any other matcher value or any
    hook command.
    """
    modified: list[str] = []
    for fname in ("settings.json", "settings.local.json"):
        result = _strip_pycache_row_from_settings_file(
            root / ".claude" / fname, root
        )
        if result:
            modified.append(result)
    return modified


def _strip_pycache_row_legacy_single_path(root: Path) -> str | None:
    """Backward-compat shim. Returns the relative path of the first file
    modified by `_strip_pycache_row_from_claude_settings`, or None.

    The C7 (1p3ay) migration code called `_strip_pycache_row_from_claude_settings`
    expecting a `str | None` return shape. C5 (1p3b7 F4) changed the signature
    to return a list. The shim preserves the old shape for any external caller
    that imported the old name. Internal callers use the new list-returning
    form.
    """
    result = _strip_pycache_row_from_claude_settings(root)
    if not result:
        return None
    return result[0]


# --- Migration report writer -------------------------------------------------


def _write_migration_report(root: Path, sections: list[tuple[str, list[str]]]) -> Path | None:
    """Write a consolidated migration report to .wavefoundry/logs/.

    ``sections`` is a list of (migration-name, action-records) tuples. An
    action-records list may include normal action descriptions and
    exception-trace strings (prefixed ``ERROR:`` by callers).

    Returns the report path when a report was written; None when no section
    had any records.
    """
    if not any(records for _name, records in sections):
        return None
    logs_dir = root / ".wavefoundry" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    report_path = logs_dir / "upgrade-migration-1.5.0.log"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"# Upgrade migration 1.4.x → 1.5.0",
        f"# Run timestamp: {timestamp}",
        "",
    ]
    for name, records in sections:
        if not records:
            continue
        lines.append(f"## {name}")
        for rec in records:
            lines.append(f"- {rec}")
        lines.append("")
    try:
        report_path.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        return None
    return report_path


# --- Preview helpers (Wave 1p3b9 / 1p3b6: --dry-run support) -----------------
#
# Each preview helper has the same signature and contract as its action
# companion, EXCEPT it performs ZERO filesystem mutations and returns the
# planned-action list instead. Used by `post_extract` when `ctx.dry_run` is
# True so operators can review what the migration WOULD do before committing.


def _preview_role_field_backfill(root: Path) -> list[str]:
    """Preview variant of `_backfill_role_field_on_agent_docs`. Returns the
    list of repository-relative paths that WOULD have `Role: <slug>` inserted,
    formatted as ``<path>: would insert Role: <slug>``. Zero filesystem
    mutations."""
    planned: list[str] = []
    agents_root = root / "docs" / "agents"
    if not agents_root.is_dir():
        return planned
    # Wave 1p3b9 (1p3b7 F6): recursive walk parallels the action helper.
    try:
        candidates = sorted(agents_root.rglob("*.md"))
    except OSError:
        return planned
    for path in candidates:
        if not path.is_file():
            continue
        if path.name in _AGENT_DOC_ROLE_EXEMPT_NAMES:
            continue
        if "journals" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _ROLE_LINE_RE.search(text):
            continue
        # Detect whether either anchor (Status:/Owner:) is present so the
        # preview matches the action helper's would-skip-no-anchor logic.
        if not (_STATUS_LINE_RE.search(text) or _OWNER_LINE_RE.search(text)):
            continue
        stem = path.stem
        try:
            rel = str(path.relative_to(root)).replace("\\", "/")  # wave 1p9hm: forward-slash
        except ValueError:
            rel = str(path)
        planned.append(f"{rel}: would insert `Role: {stem}`")
    return planned


def _preview_pycache_launcher_deletion(root: Path) -> list[str]:
    """Preview variant of `_delete_pycache_hook_launchers`. Returns the list
    of launcher files that WOULD be deleted. Zero filesystem mutations."""
    planned: list[str] = []
    hooks_dir = root / ".claude" / "hooks"
    if not hooks_dir.is_dir():
        return planned
    for name in _PYCACHE_LAUNCHER_NAMES:
        path = hooks_dir / name
        if path.exists():
            try:
                rel = str(path.relative_to(root)).replace("\\", "/")  # wave 1p9hm: forward-slash
            except ValueError:
                rel = str(path)
            planned.append(f"would delete {rel}")
    return planned


def _preview_settings_pycache_strip(root: Path) -> dict | None:
    """Preview variant of `_strip_pycache_row_from_claude_settings`. Returns
    a description of the FIRST row that WOULD be stripped (across both
    `settings.json` and `settings.local.json` per wave 1p3b9 / 1p3b7 F4),
    or None when no row matches in either file. Zero filesystem mutations."""
    for fname in ("settings.json", "settings.local.json"):
        settings_path = root / ".claude" / fname
        if not settings_path.is_file():
            continue
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        hooks_block = data.get("hooks")
        if not isinstance(hooks_block, dict):
            continue
        post_tool = hooks_block.get("PostToolUse")
        if not isinstance(post_tool, list):
            continue
        for entry in post_tool:
            if not _is_retired_pycache_row(entry):
                continue
            command = entry["hooks"][0]["command"]
            try:
                rel = str(settings_path.relative_to(root)).replace("\\", "/")  # wave 1p9hm: forward-slash
            except ValueError:
                rel = str(settings_path)
            return {
                "file": rel,
                "matcher": entry.get("matcher"),
                "command": command,
                "note": "would strip this PostToolUse Bash row",
            }
    return None


def _write_migration_preview_report(
    root: Path, sections: list[tuple[str, list[str]]],
) -> Path | None:
    """Wave 1p3b9 (1p3b6): write the preview-log to a DISTINCT filename so a
    dry-run report doesn't shadow a subsequent real-run report. Mirrors
    `_write_migration_report` shape but lands at `.preview.log`."""
    if not any(records for _name, records in sections):
        return None
    logs_dir = root / ".wavefoundry" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    report_path = logs_dir / "upgrade-migration-1.5.0.preview.log"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Upgrade migration 1.4.x → 1.5.0 — PREVIEW (--dry-run; zero mutations performed)",
        f"# Run timestamp: {timestamp}",
        "",
    ]
    for name, records in sections:
        if not records:
            continue
        lines.append(f"## {name}")
        for rec in records:
            lines.append(f"- {rec}")
        lines.append("")
    try:
        report_path.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        return None
    return report_path


# --- Convergence migration (wave 1p3iv / 1p3j7; self-contained as of 1p5b4) -------
#
# Rewrites legacy config keys to their canonical names in `docs/workflow-config.json`.
# Runs on EVERY upgrade (no version gate) — idempotent because already-canonical configs
# no-op. Operators on legacy spellings (`wave_council_policy`, `wave_execution`) get
# auto-converted at upgrade time so the deprecation window closes.
#
# Wave 1p5b4: the canonical-names manifest was retired; this convergence is now the only
# remaining piece — a self-contained hardcoded table, kept as the one-shot safety net for
# skip-version operators. Slated for removal at 2.0.0 (by then every maintained project has
# converged on upgrade).
_CONFIG_KEY_RENAMES = {
    "wave_execution": "wave_implement",
    "wave_council_policy": "wave_review",
}


def _load_config_key_renames(repo_root):
    """Return {legacy: canonical} for the config-key convergence migration.
    Self-contained (no manifest) as of wave 1p5b4; the whole migration is removed at 2.0.0.
    ``repo_root`` is accepted for call-site compatibility and unused."""
    return dict(_CONFIG_KEY_RENAMES)


def _preview_legacy_config_key_rewrite(repo_root):
    """Plan the rewrite without touching disk. Returns a list of human-readable
    planned-action strings; empty list when no work would be done."""
    workflow_config = repo_root / "docs/workflow-config.json"
    if not workflow_config.exists():
        return []
    try:
        data = json.loads(workflow_config.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, dict):
        return []
    renames = _load_config_key_renames(repo_root)
    planned = []
    for legacy, canonical in renames.items():
        if legacy in data and canonical not in data:
            planned.append(
                f"would rename `{legacy}` → `{canonical}` in docs/workflow-config.json"
            )
        elif legacy in data and canonical in data:
            planned.append(
                f"would drop legacy `{legacy}` (canonical `{canonical}` already present) "
                f"in docs/workflow-config.json"
            )
    return planned


def _rewrite_legacy_config_keys(repo_root):
    """Rewrite legacy keys to canonical in workflow-config.json. Returns a
    list of (legacy, canonical, action, dropped_value) tuples for the renames
    performed. `action` is ``"rename"`` (legacy → canonical) or ``"drop"``
    (canonical already present; legacy entry removed). `dropped_value` is
    the JSON value the legacy key held (only populated when action == "drop",
    None otherwise) — included so operators recovering from the migration log
    can see what was dropped without consulting git history. Idempotent —
    no-op when no legacy keys are present."""
    workflow_config = repo_root / "docs/workflow-config.json"
    if not workflow_config.exists():
        return []
    try:
        data = json.loads(workflow_config.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        # 1p5do: do not no-op silently — a malformed config that can't be rewritten will later fail
        # the docs gate with no migration-side signal, making the gate failure baffling. Warn here so
        # the operator can connect the gate failure to the un-migrated config.
        print(
            f"  WARNING: convergence migration could not read/parse {workflow_config} ({exc}); "
            "legacy config keys were NOT rewritten — the docs gate may fail until this is fixed.",
            file=sys.stderr,
        )
        return []
    if not isinstance(data, dict):
        print(
            f"  WARNING: convergence migration found {workflow_config} is not a JSON object; "
            "legacy config keys were NOT rewritten.",
            file=sys.stderr,
        )
        return []
    renames = _load_config_key_renames(repo_root)
    performed = []
    # Build a new dict preserving original key order with renames applied,
    # so the on-disk file remains diffable across upgrades.
    new_data = {}
    for key, value in data.items():
        if key in renames:
            canonical = renames[key]
            if canonical in data:
                # Canonical already present: drop the legacy entry. Record
                # the dropped value so operators recovering from the log can
                # see what was thrown away.
                performed.append((key, canonical, "drop", value))
                continue
            new_data[canonical] = value
            performed.append((key, canonical, "rename", None))
        else:
            new_data[key] = value
    if not performed:
        return []
    workflow_config.write_text(
        json.dumps(new_data, indent=2) + "\n",
        encoding="utf-8",
    )
    return performed


def _write_convergence_preview_report(root, planned):
    """Wave 1p3iv (1p3j7): write the convergence dry-run preview to a
    distinct log file for parity with `_write_migration_preview_report`.
    Operators running `--dry-run` get a written record to review before
    committing to the real upgrade."""
    if not planned:
        return None
    logs_dir = root / ".wavefoundry" / "logs"
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    report_path = logs_dir / "upgrade-convergence-migration.preview.log"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Upgrade convergence migration — PREVIEW (--dry-run; zero mutations performed)",
        f"# Run timestamp: {timestamp}",
        "",
        "## Legacy config-key rewrite (1p3j7 — convergence half)",
    ]
    for record in planned:
        lines.append(f"- {record}")
    lines.append("")
    try:
        report_path.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        return None
    return report_path


def _write_convergence_report(root, performed):
    """Wave 1p3iv (1p3j7): write the convergence real-run log alongside the
    1.5.0 migration report for parity. Records each rename / drop with the
    dropped value (when applicable) so operators recovering from a surprise
    can read the log instead of consulting git."""
    if not performed:
        return None
    logs_dir = root / ".wavefoundry" / "logs"
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    report_path = logs_dir / "upgrade-convergence-migration.log"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Upgrade convergence migration — REAL RUN",
        f"# Run timestamp: {timestamp}",
        "",
        "## Legacy config-key rewrite (1p3j7 — convergence half)",
    ]
    for legacy, canonical, action, dropped_value in performed:
        if action == "rename":
            lines.append(
                f"- renamed `{legacy}` → `{canonical}` in docs/workflow-config.json"
            )
        else:  # drop
            value_repr = json.dumps(dropped_value)
            lines.append(
                f"- dropped legacy `{legacy}` (canonical `{canonical}` already "
                f"present in docs/workflow-config.json); dropped value was: "
                f"`{value_repr}`"
            )
    lines.append("")
    try:
        report_path.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        return None
    return report_path


def _run_convergence_migration(ctx):
    """Top-level convergence migration. Always runs (no version gate).
    Records to a dedicated log file and stderr; silent no-op when no renames
    apply. Dry-run writes to `.preview.log`; real-run writes to `.log`."""
    try:
        if getattr(ctx, "dry_run", False):
            planned = _preview_legacy_config_key_rewrite(ctx.root)
            if planned:
                report_path = _write_convergence_preview_report(ctx.root, planned)
                tail = f" — see {report_path}" if report_path else ""
                print(
                    f"upgrade-convergence preview: {len(planned)} legacy "
                    f"config-key rewrite(s) planned in docs/workflow-config.json{tail}",
                    file=sys.stderr,
                )
                for record in planned:
                    print(f"  - {record}", file=sys.stderr)
        else:
            performed = _rewrite_legacy_config_keys(ctx.root)
            if performed:
                # Build a compact summary that distinguishes rename from drop
                # so the stderr line isn't misleading on the both-present case.
                renames = [
                    f"`{l}`→`{c}`" for l, c, action, _v in performed
                    if action == "rename"
                ]
                drops = [
                    f"`{l}` (canonical `{c}` already present)"
                    for l, c, action, _v in performed
                    if action == "drop"
                ]
                report_path = _write_convergence_report(ctx.root, performed)
                tail = f" — see {report_path} for the dropped values" if report_path else ""
                parts = []
                if renames:
                    parts.append(f"renamed {len(renames)} ({', '.join(renames)})")
                if drops:
                    parts.append(f"dropped {len(drops)} ({', '.join(drops)})")
                print(
                    f"upgrade-convergence: {'; '.join(parts)} in "
                    f"docs/workflow-config.json{tail}",
                    file=sys.stderr,
                )
    except Exception:  # pragma: no cover — defensive isolation
        print(
            f"upgrade-convergence: ERROR: {traceback.format_exc()}",
            file=sys.stderr,
        )


# --- Wired hook --------------------------------------------------------------


def post_extract(ctx):
    """1.4.x → 1.5.0 migration hook.

    Runs only when ``ctx.from_version`` predates 1.5.0. Each migration is
    isolated in its own try/except so a failure in one does not abort the
    others; failures are recorded in the report rather than raised.

    Wave 1p3b9 (1p3b6): when ``ctx.dry_run`` is True, the preview helpers
    fire instead of the action helpers — zero filesystem mutations, preview
    output written to a DISTINCT filename
    (``upgrade-migration-1.5.0.preview.log``) so it does not shadow a
    subsequent real-run report. Operators can review the planned actions
    before committing to the real upgrade.

    Wave 1p3iv (1p3j7): the convergence migration runs FIRST, before the
    1.4 → 1.5 version gate, on every upgrade. It rewrites legacy config keys to
    canonical in ``docs/workflow-config.json``. Idempotent — no-op when no legacy
    keys are present. (Wave 1p5b4: the rename map is now a self-contained hardcoded
    table — the canonical-names manifest was retired; this convergence is removed at 2.0.0.)
    """
    # Wave 1p3iv (1p3j7): convergence half — runs on every upgrade.
    _run_convergence_migration(ctx)

    if not _from_version_predates(ctx.from_version, "1.5.0"):
        return

    # Wave 1p3b9 (1p3b6): dry-run branch. UpgradeContext gained `dry_run` so
    # we can preview without touching disk. Fall back to False for older
    # contexts (`getattr` default) — the field is new in 1.5.0.
    if getattr(ctx, "dry_run", False):
        preview_sections: list[tuple[str, list[str]]] = []
        try:
            planned = _preview_role_field_backfill(ctx.root)
            preview_sections.append((
                "Role: backfill on docs/agents/*.md "
                "(C4 / 1p35l: docs-lint now enforces Role: on every agent doc)",
                planned,
            ))
        except Exception:
            preview_sections.append((
                "Role: backfill on docs/agents/*.md",
                [f"ERROR (preview): {traceback.format_exc()}"],
            ))
        try:
            planned = _preview_pycache_launcher_deletion(ctx.root)
            preview_sections.append((
                "Pycache launcher cleanup "
                "(C5 / 1p35n: .claude/hooks/pycache-cleanup* retired)",
                planned,
            ))
        except Exception:
            preview_sections.append((
                "Pycache launcher cleanup",
                [f"ERROR (preview): {traceback.format_exc()}"],
            ))
        try:
            row = _preview_settings_pycache_strip(ctx.root)
            preview_sections.append((
                "Claude Code settings.json pycache row removal "
                "(C5 / 1p35n: PostToolUse Bash → pycache-cleanup row retired)",
                [f"would strip from {row['file']}: matcher={row['matcher']!r} "
                 f"command={row['command']!r}"] if row else [],
            ))
        except Exception:
            preview_sections.append((
                "Claude Code settings.json pycache row removal",
                [f"ERROR (preview): {traceback.format_exc()}"],
            ))
        report_path = _write_migration_preview_report(ctx.root, preview_sections)
        total = sum(len(recs) for _name, recs in preview_sections)
        if total > 0:
            print(
                f"upgrade-migration preview: {total} planned action(s); "
                f"see {report_path} for details (no files modified)",
                file=sys.stderr,
                flush=True,
            )
        return

    sections: list[tuple[str, list[str]]] = []

    # Migration 1: Role: backfill
    try:
        modified = _backfill_role_field_on_agent_docs(ctx.root)
        sections.append((
            "Role: backfill on docs/agents/*.md "
            "(C4 / 1p35l: docs-lint now enforces Role: on every agent doc)",
            [f"inserted `Role: <slug>` into {rel}" for rel in modified],
        ))
    except Exception:  # pragma: no cover — defensive isolation
        sections.append((
            "Role: backfill on docs/agents/*.md",
            [f"ERROR: {traceback.format_exc()}"],
        ))

    # Migration 2: Pycache launcher cleanup
    try:
        deleted = _delete_pycache_hook_launchers(ctx.root)
        sections.append((
            "Pycache launcher cleanup "
            "(C5 / 1p35n: .claude/hooks/pycache-cleanup* retired)",
            [f"deleted {rel}" for rel in deleted],
        ))
    except Exception:  # pragma: no cover — defensive isolation
        sections.append((
            "Pycache launcher cleanup",
            [f"ERROR: {traceback.format_exc()}"],
        ))

    # Migration 3: settings.json pycache row strip (covers both committed
    # `.claude/settings.json` AND personal-override `.claude/settings.local.json`
    # per wave 1p3b9 / 1p3b7 F4).
    try:
        modified_settings = _strip_pycache_row_from_claude_settings(ctx.root)
        sections.append((
            "Claude Code settings.json pycache row removal "
            "(C5 / 1p35n: PostToolUse Bash → pycache-cleanup row retired; "
            "1p3b7 F4 added settings.local.json coverage)",
            [f"stripped PostToolUse Bash → pycache-cleanup row from {rel}"
             for rel in modified_settings],
        ))
    except Exception:  # pragma: no cover — defensive isolation
        sections.append((
            "Claude Code settings.json pycache row removal",
            [f"ERROR: {traceback.format_exc()}"],
        ))

    _write_migration_report(ctx.root, sections)

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
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path

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

    candidate_dirs = [agents_root, agents_root / "specialists", agents_root / "personas"]
    for candidate in candidate_dirs:
        if not candidate.is_dir():
            continue
        try:
            entries = sorted(candidate.iterdir())
        except OSError:
            continue
        for path in entries:
            if not path.is_file() or path.suffix != ".md":
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
                modified.append(str(path.relative_to(root)))
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
            deleted.append(str(path.relative_to(root)))
        except ValueError:
            deleted.append(str(path))
    return deleted


# --- Migration 3: settings.json pycache row strip ----------------------------


def _strip_pycache_row_from_claude_settings(root: Path) -> str | None:
    """Remove the retired ``PostToolUse`` Bash → pycache-cleanup hook row.

    Returns the relative path of ``.claude/settings.json`` when modified,
    else None. Preserves all other hook rows including operator-added customs.

    Matches a hook block whose ``matcher == "Bash"`` AND whose nested
    ``hooks[0].command`` ends with ``pycache-cleanup`` or
    ``pycache-cleanup.cmd`` (case-insensitive on Windows paths). Does not
    touch any other matcher value or any hook command.
    """
    settings_path = root / ".claude" / "settings.json"
    if not settings_path.is_file():
        return None
    try:
        text = settings_path.read_text(encoding="utf-8")
        data = json.loads(text)
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

    def _is_retired_pycache_row(entry: dict) -> bool:
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

    original_len = len(post_tool)
    post_tool_filtered = [e for e in post_tool if not _is_retired_pycache_row(e)]
    if len(post_tool_filtered) == original_len:
        return None  # no-op; preserve mtime

    hooks_block["PostToolUse"] = post_tool_filtered
    try:
        settings_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        return None
    try:
        return str(settings_path.relative_to(root))
    except ValueError:
        return str(settings_path)


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


# --- Wired hook --------------------------------------------------------------


def post_extract(ctx):
    """1.4.x → 1.5.0 migration hook.

    Runs only when ``ctx.from_version`` predates 1.5.0. Each migration is
    isolated in its own try/except so a failure in one does not abort the
    others; failures are recorded in the report rather than raised.
    """
    if not _from_version_predates(ctx.from_version, "1.5.0"):
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

    # Migration 3: settings.json pycache row strip
    try:
        modified_settings = _strip_pycache_row_from_claude_settings(ctx.root)
        sections.append((
            "Claude Code settings.json pycache row removal "
            "(C5 / 1p35n: PostToolUse Bash → pycache-cleanup row retired)",
            [f"stripped PostToolUse Bash → pycache-cleanup row from {modified_settings}"]
            if modified_settings else [],
        ))
    except Exception:  # pragma: no cover — defensive isolation
        sections.append((
            "Claude Code settings.json pycache row removal",
            [f"ERROR: {traceback.format_exc()}"],
        ))

    _write_migration_report(ctx.root, sections)

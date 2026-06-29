#!/usr/bin/env python3
"""Upgrade-time retired-surface reconciliation scan (wave 1p8et).

When a minor-or-major upgrade RETIRES or RENAMES a framework surface, every reference in a consumer's
repo-authored docs/configs to the old surface becomes a broken instruction. The live example: the
1.9.0 cutover retired the per-command ``.wavefoundry/bin/*`` wrappers for the cross-OS ``wf``
dispatcher, so a doc naming ``.wavefoundry/bin/docs-lint`` is now wrong.

This module is the SHIPPED, shared home for the proven scan logic that previously lived ONLY as a
unittest guard (``tests/test_wf_cli.py`` → ``NoLiveReferenceToRetiredWrapperTests``) that
``build_pack.py`` strips from the distribution. The patterns + exclusion set are lifted here verbatim
so:

  * the upgrade reconciliation phase (``upgrade_wavefoundry.py``) can RUN the scan downstream, and
  * the self-host test guard repoints at this single source (no duplicated regex).

The retired→new mapping is NOT re-authored here — it is imported from
``render_platform_surfaces._RETIRED_SURFACE_REPLACEMENTS`` (the ONE table, co-located with
``_RETIRED_BIN_WRAPPERS``). The scan, the seed example, and the upgrade recommendation all consume that
one map.

Default REPORT-ONLY: this module never mutates repo files. The exclusion set is baked in so the scan
never flags the framework pack tree, the generated index, wave/report history, any `CHANGELOG.md`
(by basename, anywhere), the renderer-managed `prompt-surface-manifest.json`, journals/snapshots, or
test files.

Reconciliation is UPGRADE-TIME-ONLY: this helper is called from the upgrade reconciliation phase. It
is intentionally NOT wired to a standalone ``wf reconcile`` CLI subcommand or a ``wave_reconcile`` MCP
tool (operator decision 2026-06-27 — a reference only goes stale crossing a version boundary).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

# ── The one shared retired→new map ────────────────────────────────────────────
# Imported, never re-authored. ``_RETIRED_SURFACE_REPLACEMENTS`` is co-located with
# ``_RETIRED_BIN_WRAPPERS`` in render_platform_surfaces.py; ``retired_surface_suggestion`` resolves
# the human-facing replacement form (``wf <subcommand>`` or the no-replacement guidance).
from render_platform_surfaces import (  # noqa: E402 — SCRIPTS_DIR is on sys.path
    _RETIRED_SURFACE_REPLACEMENTS,
    retired_surface_suggestion,
)

# Retired surface names, derived from the one map (so adding/retiring a surface there flows here).
RETIRED_SURFACES: tuple[str, ...] = tuple(_RETIRED_SURFACE_REPLACEMENTS)

_RETIRED_ALT = "|".join(re.escape(w) for w in RETIRED_SURFACES)

# ── Patterns (lifted verbatim from NoLiveReferenceToRetiredWrapperTests) ──────

# 1. Literal `.wavefoundry/bin/<wrapper>` reference (word-boundary after the name). The bin separator
#    is a char class `[\\/]` so BOTH POSIX (`.wavefoundry/bin/docs-lint`) and Windows-backslash
#    (`.wavefoundry\bin\docs-lint`) and mixed (`.wavefoundry/bin\docs-lint`) references are caught —
#    a consumer doc on Windows that writes backslash paths would otherwise be a silent false negative.
_LITERAL_PATTERN = re.compile(
    r"\.wavefoundry[\\/]bin[\\/](" + _RETIRED_ALT + r")(?![\w-])"
)

# 2. Dynamic path-join: `"bin" / "<wrapper>"` (e.g. the pre-1p7tz
#    `REPO_ROOT / ".wavefoundry" / "bin" / "docs-lint"`). A literal-string scan misses these.
_DYNAMIC_PATTERN = re.compile(
    r"""["']bin["']\s*/\s*["'](""" + _RETIRED_ALT + r""")["']"""
)

# 3. Variable bin-dir join: `<bin-ish var> / "<wrapper>"` (e.g. `bin_dir / "docs-lint"`). Because
#    `wf` and the `_RETIRED_BIN_WRAPPERS` tuple entries are NOT retired NAMES being joined as strings
#    here, `bin_dir / "wf"` and the renderer's own deletion list never match.
_VAR_BINDIR_PATTERN = re.compile(
    r"""\b\w*bin\w*\s*/\s*["'](""" + _RETIRED_ALT + r""")["']"""
)

# ── Exclusion set ─────────────────────────────────────────────────────────────
# Directory exclusions matched on path COMPONENT/PREFIX (NOT raw substring) — mirrors
# ``build_pack.should_exclude`` (``rel == d or rel.startswith(d + "/")``). Raw substring matching
# over-excludes in-scope operator docs: e.g. `docs/reports-overview.md` is NOT under `docs/reports/`,
# and a substring check would wrongly drop it. The framework pack tree, generated index, wave/report
# history, and vcs/build dirs are excluded; ``docs/reports`` is the change doc's added history root.
EXCLUDED_DIRS: tuple[str, ...] = (
    ".git",
    "__pycache__",
    "node_modules",
    ".wavefoundry/framework",  # the framework pack tree — its own source legitimately names them
    ".wavefoundry/index",      # generated/runtime semantic index artifacts
    "docs/waves",              # wave history records
    "docs/reports",            # report history
)
# File-name exclusions matched on BASENAME anywhere in the tree (not root-only). A file named
# `CHANGELOG.md` is release history wherever it lives (e.g. a nested `.wavefoundry/CHANGELOG.md`), and
# `prompt-surface-manifest.json` is a renderer-managed generated manifest whose historical
# `upgrade_merge_notes` cause false positives — like the generated index, it is not operator-authored.
EXCLUDED_BASENAMES: tuple[str, ...] = ("CHANGELOG.md", "prompt-surface-manifest.json")

# History directories matched on a path COMPONENT (not substring): a file *under* `journals/` or
# `snapshots/` is history. This no longer drops `src/snapshotter.py` (substring `snapshot`) or a doc
# whose name merely contains `journal`.
_EXCLUDED_PATH_COMPONENTS: tuple[str, ...] = ("journals", "snapshots")

SCAN_SUFFIXES: tuple[str, ...] = (".md", ".mdc", ".json", ".py")

# ── Host permission / allow-rule files (separate operator-flag channel) ───────
# seed-160: the scan "does NOT cover host permission/allow-rule files" — they must be surfaced
# SEPARATELY for the operator, not folded into the edit-these `reconciliation` list, because an agent
# cannot self-edit these under host auto-mode guards. They are still SCANNED (a renamed surface can
# leave a stale command in an allow rule), but a hit is classified into the host-permission channel so
# the operator (not the agent) makes the edit. Matched by exact repo-relative POSIX path: these are the
# canonical host permission/allow-rule files (Claude Code allow rules + Cursor settings).
HOST_PERMISSION_FILES: frozenset[str] = frozenset({
    ".claude/settings.local.json",  # Claude Code permission allow rules (operator-owned)
    ".claude/settings.json",        # Claude Code project settings / hook+permission wiring
    ".cursor/settings.json",        # Cursor project settings / permissions
})


def is_host_permission_file(rel: str) -> bool:
    """Return True when *rel* (repo-relative POSIX path) is a host permission/allow-rule file.

    These are scanned but routed to the separate operator-flag channel (see ``HOST_PERMISSION_FILES``)
    rather than the editable ``reconciliation`` list — an agent cannot self-edit them under host
    auto-mode guards.
    """
    return rel in HOST_PERMISSION_FILES


@dataclass(frozen=True)
class StaleReference:
    """One stale retired-surface reference found in a repo-authored file.

    ``file`` is the repo-relative POSIX path; ``line`` is 1-based; ``retired_surface`` is the matched
    retired name; ``matched`` is the actual matched substring (the literal `.wavefoundry/bin/<name>`
    path, or the `"bin" / "<name>"` / `<bin-var> / "<name>"` join text) so callers print the real
    reference rather than assuming a `.wavefoundry/bin/<name>` form (which is wrong for the .py-join
    findings); ``suggested`` is the replacement guidance (``wf <subcommand>`` or, for the
    no-replacement case, the remove/rewrite guidance). ``host_permission`` is True when the hit is in a
    host permission/allow-rule file (``HOST_PERMISSION_FILES``) — those go to the separate
    operator-flag channel, not the editable ``reconciliation`` list (an agent cannot self-edit them).
    """

    file: str
    line: int
    retired_surface: str
    matched: str
    suggested: str
    host_permission: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "file": self.file,
            "line": self.line,
            "retired_surface": self.retired_surface,
            "matched": self.matched,
            "suggested": self.suggested,
        }


def is_excluded(rel: str, *, name: str, suffix: str) -> bool:
    """Return True when a repo-relative path is outside the reconciliation scan scope.

    ``rel`` is the POSIX repo-relative path; ``name`` the file name; ``suffix`` the file extension.
    Bakes in the full exclusion set: unscannable suffixes, the framework pack tree, the generated
    index, wave/report history, the changelog and renderer-managed manifest (matched by BASENAME
    anywhere), journals/snapshots, and test files. Directory exclusions match on path COMPONENT/PREFIX
    (not raw substring) so in-scope near-miss docs like ``docs/reports-overview.md`` and
    ``src/snapshotter.py`` are NOT dropped.
    """
    if suffix not in SCAN_SUFFIXES:
        return True
    parts = rel.split("/")
    # Directory exclusions: exact path or path-prefix (mirror build_pack.should_exclude). The single-
    # component dirs (.git/__pycache__/node_modules) are also matched as a path component anywhere.
    for d in EXCLUDED_DIRS:
        if rel == d or rel.startswith(d + "/"):
            return True
        if "/" not in d and d in parts:
            return True
    # File-name exclusions matched by BASENAME anywhere: CHANGELOG.md is release history wherever it
    # lives (incl. a nested `.wavefoundry/CHANGELOG.md`); prompt-surface-manifest.json is a generated,
    # renderer-managed manifest whose historical upgrade_merge_notes are not operator-authored refs.
    if name in EXCLUDED_BASENAMES:
        return True
    # Journals / snapshots are history — matched on a path component, not a substring.
    if any(c in parts for c in _EXCLUDED_PATH_COMPONENTS):
        return True
    # Test files name the retired surfaces to assert they are gone (a `tests/` component + `test_`
    # filename), anywhere in the tree — not just the framework tests dir.
    if "tests" in parts and name.startswith("test_"):
        return True
    return False


def _iter_scannable_files(root: Path) -> Iterator[tuple[Path, str]]:
    """Yield ``(path, repo_relative_posix)`` for every in-scope file under ``root``."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if is_excluded(rel, name=path.name, suffix=path.suffix):
            continue
        yield path, rel


def scan_repo(root: Path | str) -> list[StaleReference]:
    """Scan ``root`` for stale references to retired framework surfaces (ALL findings, both channels).

    Returns a list of :class:`StaleReference` (file, line, retired_surface, matched, suggested,
    host_permission). REPORT-ONLY — never mutates any file. The exclusion set is baked in (see
    :func:`is_excluded`). Each finding's ``host_permission`` flag is set when its file is a host
    permission/allow-rule file (see :func:`is_host_permission_file`); :func:`scan_repo_channels`
    partitions on that flag. Sorted by (file, line, retired_surface) for deterministic output.

    Catches three reference forms: the literal ``.wavefoundry/bin/<wrapper>`` path (docs/config), the
    dynamic ``"bin" / "<wrapper>"`` join, and the variable ``<bin-var> / "<wrapper>"`` join (scripts).
    The literal form is scanned in every in-scope suffix; the dynamic/variable join forms are scanned
    only in ``.py`` files (they are a Python-construction concern).
    """
    root = Path(root)
    findings: list[StaleReference] = []
    for path, rel in _iter_scannable_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        host_perm = is_host_permission_file(rel)
        patterns = [_LITERAL_PATTERN]
        if path.suffix == ".py":
            patterns += [_DYNAMIC_PATTERN, _VAR_BINDIR_PATTERN]
        for pat in patterns:
            for m in pat.finditer(text):
                retired = m.group(1)
                line = text.count("\n", 0, m.start()) + 1
                findings.append(
                    StaleReference(
                        file=rel,
                        line=line,
                        retired_surface=retired,
                        matched=m.group(0),
                        suggested=retired_surface_suggestion(retired),
                        host_permission=host_perm,
                    )
                )
    findings.sort(key=lambda f: (f.file, f.line, f.retired_surface))
    return findings


def scan_repo_channels(
    root: Path | str,
) -> tuple[list[StaleReference], list[StaleReference]]:
    """Scan ``root`` and partition findings into the TWO operator channels.

    Returns ``(reconciliation, host_permission_flags)``:

    * ``reconciliation`` — stale refs in editable repo docs/prompts/configs/scripts. The agent applies
      each suggested edit itself.
    * ``host_permission_flags`` — stale refs in host permission/allow-rule files
      (``HOST_PERMISSION_FILES``). The agent CANNOT self-edit these under host auto-mode guards, so
      they are flagged for the operator to edit (seed-160 "flagged separately for the operator").

    Both lists hold :class:`StaleReference` in the same deterministic (file, line, retired_surface)
    order produced by :func:`scan_repo`.
    """
    reconciliation: list[StaleReference] = []
    host_permission_flags: list[StaleReference] = []
    for ref in scan_repo(root):
        (host_permission_flags if ref.host_permission else reconciliation).append(ref)
    return reconciliation, host_permission_flags

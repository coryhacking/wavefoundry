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

Wave 1u2az adds a THIRD channel: stale allow rules in the committed `.claude/settings.json` that
fall inside the permissions renderer's provenance key are SELF-HEALING (the next upgrade/install
permissions render prunes/replaces them) and are partitioned into ``renderer_provenance_flags``
rather than the operator's ``host_permission_flags`` channel. Membership is decided only by exact
provenance membership AND the hit's location inside an allow/provenance array (the only regions the
render rewrites), never by the ``mcp__wavefoundry__`` name prefix and never by substring
containment — a stale rule elsewhere in that file, e.g. inside a hooks command, is operator
territory because no render will ever fix it.

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
    PERMISSIONS_PROVENANCE_KEY,
    _RENAMED_MCP_TOOLS,
    _RETIRED_SURFACE_REPLACEMENTS,
    renamed_tool_suggestion,
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

# ── Renamed MCP tools (wave 1t72b / 1.14.0 rename) ────────────────────────────
# Old tool names, longest-first so alternation can never match a shorter name
# inside a longer one (`wave_index_build` inside `wave_index_build_status`).
RENAMED_TOOLS: tuple[str, ...] = tuple(
    sorted(_RENAMED_MCP_TOOLS, key=len, reverse=True)
)

# `wave_review` and `wave_implement` are legitimate workflow-config KEYS as
# well as old tool names. Flagging their bare-token form would instruct agents
# to rename config keys — actively breaking target workflow configs — so bare
# matching skips them; only the unambiguous `mcp__wavefoundry__` tool-call
# form flags these two.
_CONFIG_KEY_TOOL_NAMES: frozenset[str] = frozenset({"wave_review", "wave_implement"})

_RENAMED_ALT_ALL = "|".join(re.escape(n) for n in RENAMED_TOOLS)
_RENAMED_ALT_BARE = "|".join(
    re.escape(n) for n in RENAMED_TOOLS if n not in _CONFIG_KEY_TOOL_NAMES
)

# 4. Fully-qualified MCP tool reference (host allow rules, MCP client configs):
#    `mcp__wavefoundry__wave_close`. Trailing guard: `_` and word chars end the
#    match honestly via the alternation's longest-first ordering plus `(?![\w])`.
_TOOL_MCP_PATTERN = re.compile(
    r"mcp__wavefoundry__(" + _RENAMED_ALT_ALL + r")(?!\w)"
)

# 5. Bare tool-name reference in docs/prompts/scripts: `wave_close(...)`,
#    backticked names, allowlists. Word-boundary on both sides; the two
#    workflow-config key names are excluded (see _CONFIG_KEY_TOOL_NAMES).
_TOOL_BARE_PATTERN = re.compile(
    r"(?<![\w.])(" + _RENAMED_ALT_BARE + r")(?!\w)"
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
    ".wavefoundry/upgrade-assets",  # retained protocol-bridge payload/recovery artifacts
    "docs/waves",              # wave history records
    "docs/reports",            # report history
    "docs/agents/memory",      # memory records quote history; the memory corpus has its own hygiene loop
)
# Protocol-bridge upgrades retain the previous framework tree under a generated sibling such as
# ``.wavefoundry/framework.rollback-bridge-pfps-p2/``.  It is inactive recovery state, not a live
# project carrier.  Keep this separate from ``EXCLUDED_DIRS`` because it is a component prefix, not
# one fixed directory name.
_FRAMEWORK_ROLLBACK_DIR_PREFIX = "framework.rollback-"
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


# ── Renderer-provenance allow rules (self-healing channel, wave 1u2az) ────────
# The committed `.claude/settings.json` now carries a renderer-owned MCP allowlist whose exact
# emitted entries are recorded under `render_platform_surfaces.PERMISSIONS_PROVENANCE_KEY`. A stale
# reference INSIDE that provenance, in a region the render rewrites, is not operator territory: the
# next upgrade/install permissions render prunes/replaces it automatically, so the scan reports it in
# a third, SELF-HEALING channel.
# Everything else in `.claude/settings.json` (operator-authored rules, including rules that happen
# to name a wavefoundry tool, plus hook wiring — even a hooks COMMAND naming the exact same stale
# rule string), all of `.claude/settings.local.json`, and `.cursor/settings.json` remain genuinely
# operator-owned and keep routing to the host-permission channel. Ownership is decided ONLY by exact
# provenance membership plus the hit's location inside an allow/provenance array, never by the
# `mcp__wavefoundry__` name prefix.
_CLAUDE_SETTINGS_FILE = ".claude/settings.json"


def renderer_provenance_rules(root: Path | str) -> frozenset[str]:
    """The allow-rule strings the permissions renderer recorded emitting into
    `.claude/settings.json` (its provenance key).

    Fail-safe by construction: an absent or unreadable file (``OSError``), malformed JSON
    or an undecodable byte stream (``ValueError``, which covers ``json.JSONDecodeError``
    and ``UnicodeDecodeError``), a non-object payload, or a non-list provenance key all
    yield an EMPTY set, so every finding routes to the operator channel and never
    silently to the self-healing one. ``PERMISSIONS_PROVENANCE_KEY`` is resolved by this
    module's top-level import (never re-authored here and never a call-time import that
    could raise inside this helper)."""
    import json

    try:
        loaded = json.loads(
            (Path(root) / ".claude" / "settings.json").read_text(encoding="utf-8")
        )
        raw = loaded.get(PERMISSIONS_PROVENANCE_KEY) if isinstance(loaded, dict) else None
        if isinstance(raw, list):
            return frozenset(entry for entry in raw if isinstance(entry, str))
    except (OSError, ValueError):
        pass
    return frozenset()


# The two renderer-governed regions of `.claude/settings.json`, each pinned to an exact
# document position rather than to a key NAME: the top-level provenance record, and the
# `allow` array that is a direct member of the TOP-LEVEL `permissions` object. A stale rule
# anywhere else in that file (a hooks command, an operator-authored key, a `deny`/`ask`
# entry, or a foreign array that merely happens to be named `allow`) is NOT self-healing —
# the permissions render only ever rewrites these two arrays.
_PROVENANCE_ALLOW_CONTAINER_KEY = "permissions"
_PROVENANCE_ALLOW_KEY = "allow"


def _json_key_value_spans(
    text: str, key: str, *, depth: int, opener: str
) -> list[tuple[int, int]]:
    """Character spans of every ``opener``-opened value bound to ``"key"`` at object *depth*.

    Position-tracking scan (one left-to-right pass, no full parse): string literals are
    consumed whole, so brackets, braces, escaped quotes and embedded key tokens inside a
    rule string can never be mistaken for structure. A quoted token counts as a KEY only
    when the next non-whitespace character is ``:``; a string VALUE equal to the key token
    is therefore ignored.

    ``depth`` is the number of enclosing containers around the key, so a member of the root
    object is at depth 1 and a member of a top-level object's value is at depth 2. Keying on
    depth (and, for ``allow``, on containment inside the ``permissions`` object — see
    ``provenance_governed_spans``) is what keeps a foreign ``somePlugin.config.allow`` array
    out of renderer-governed territory.

    Returns ``[]`` for a key that is absent, is not at *depth*, or whose value does not open
    with ``opener``. Malformed input (an unterminated string, an unclosed array or object,
    an unbalanced closer) yields no span for the affected region, so an unrecognized shape
    degrades to "not governed" — the operator channel, which is the safe direction.
    """
    spans: list[tuple[int, int]] = []
    # Open containers, innermost last: (opening char, start offset, the key it is bound to,
    # that key's object depth). ``None`` for a container that is an array element.
    stack: list[tuple[str, int, str | None, int]] = []
    pending_key: str | None = None
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == '"':
            end = index + 1
            escaped = False
            while end < length:
                current = text[end]
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    break
                end += 1
            if end >= length:
                return spans  # unterminated string — degrade to "not governed"
            token = text[index + 1:end]
            cursor = end + 1
            while cursor < length and text[cursor].isspace():
                cursor += 1
            if cursor < length and text[cursor] == ":":
                pending_key = token
                index = cursor + 1
                continue
            pending_key = None  # a string VALUE, not a key
            index = end + 1
            continue
        if char in "{[":
            stack.append((char, index, pending_key, len(stack)))
            pending_key = None
            index += 1
            continue
        if char in "}]":
            if not stack:
                return spans  # unbalanced closer — degrade to "not governed"
            open_char, start, frame_key, frame_depth = stack.pop()
            if open_char == opener and frame_key == key and frame_depth == depth:
                spans.append((start, index + 1))
            pending_key = None
            index += 1
            continue
        if char == ",":
            pending_key = None
        index += 1
    return spans


def provenance_governed_spans(text: str) -> list[tuple[int, int]]:
    """Character spans in a `.claude/settings.json` body that the permissions render owns.

    Exactly two regions: the TOP-LEVEL provenance array, and the ``allow`` array that is a
    direct member of the TOP-LEVEL ``permissions`` object. Used to require that a stale hit
    is an allow/provenance ENTRY before calling it self-healing. An array named ``allow``
    that lives anywhere else (a plugin's own config, a nested object, a second
    ``permissions`` key deeper in the tree) is not governed: no render will ever rewrite it,
    so a hit there must stay in the operator channel.
    """
    spans: list[tuple[int, int]] = _json_key_value_spans(
        text, PERMISSIONS_PROVENANCE_KEY, depth=1, opener="["
    )
    container_spans = _json_key_value_spans(
        text, _PROVENANCE_ALLOW_CONTAINER_KEY, depth=1, opener="{"
    )
    if not container_spans:
        return spans
    for allow_start, allow_end in _json_key_value_spans(
        text, _PROVENANCE_ALLOW_KEY, depth=2, opener="["
    ):
        if any(
            start <= allow_start and allow_end <= end
            for start, end in container_spans
        ):
            spans.append((allow_start, allow_end))
    return spans


def _is_renderer_provenance_hit(
    rel: str,
    matched: str,
    provenance: frozenset[str],
    governed_spans: list[tuple[int, int]],
    offset: int,
) -> bool:
    """True when a stale hit in `.claude/settings.json` is a renderer-governed allow rule.

    THREE conditions, all required:

    * the file is the committed Claude settings file — a provenance list never reclassifies
      hits in `settings.local.json` or any other host file;
    * the matched stale text EQUALS a recorded provenance rule. Exact membership, not
      containment: the renderer emits bare ``mcp__wavefoundry__<name>`` rules (Claude Code
      MCP rules carry no argument suffixes), so a containment test could only ever fire on
      a coincidental substring and would route a rule nobody rewrites into the
      "no edit needed" channel;
    * the hit LOCATION lies inside an allow/provenance array (``governed_spans``). Without
      this, the same rule string sitting in a hooks command in the same file would be
      reported as self-healing while no render ever touches it.

    Anything that fails a condition stays operator-side, which is the safe direction.
    """
    if rel != _CLAUDE_SETTINGS_FILE or not provenance:
        return False
    if matched not in provenance:
        return False
    return any(start <= offset < end for start, end in governed_spans)


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
    ``renderer_provenance`` (wave 1u2az) is True only for hits in `.claude/settings.json` that sit
    inside an allow/provenance array AND exactly equal a rule the permissions renderer recorded
    emitting; those SELF-HEAL at the next upgrade/install permissions render and route to their own
    channel. A hit anywhere else in that file (a hooks command, an operator key) is False.
    """

    file: str
    line: int
    retired_surface: str
    matched: str
    suggested: str
    host_permission: bool = False
    renderer_provenance: bool = False

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
    if (
        len(parts) >= 3
        and parts[0] == ".wavefoundry"
        and parts[1].startswith(_FRAMEWORK_ROLLBACK_DIR_PREFIX)
    ):
        return True
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
    provenance = renderer_provenance_rules(root)
    findings: list[StaleReference] = []
    for path, rel in _iter_scannable_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        host_perm = is_host_permission_file(rel)
        # Renderer-governed regions of the committed Claude settings file (allow +
        # provenance arrays). Computed once per file; empty for every other file, so
        # `_is_renderer_provenance_hit` can only ever fire on a real allow/provenance entry.
        governed_spans = (
            provenance_governed_spans(text)
            if provenance and rel == _CLAUDE_SETTINGS_FILE
            else []
        )

        def _provenance_flag(m: re.Match[str]) -> bool:
            return _is_renderer_provenance_hit(
                rel, m.group(0), provenance, governed_spans, m.start()
            )

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
                        renderer_provenance=_provenance_flag(m),
                    )
                )
        # Renamed MCP tools (1.14.0): the fully-qualified form first; its match
        # spans are masked so the bare pattern cannot double-report the tool
        # name embedded inside `mcp__wavefoundry__<old>`.
        qualified_spans: list[tuple[int, int]] = []
        for m in _TOOL_MCP_PATTERN.finditer(text):
            qualified_spans.append(m.span())
            old_name = m.group(1)
            line = text.count("\n", 0, m.start()) + 1
            findings.append(
                StaleReference(
                    file=rel,
                    line=line,
                    retired_surface=old_name,
                    matched=m.group(0),
                    suggested=renamed_tool_suggestion(old_name),
                    host_permission=host_perm,
                    renderer_provenance=_provenance_flag(m),
                )
            )
        for m in _TOOL_BARE_PATTERN.finditer(text):
            if any(s <= m.start() < e for s, e in qualified_spans):
                continue
            old_name = m.group(1)
            line = text.count("\n", 0, m.start()) + 1
            findings.append(
                StaleReference(
                    file=rel,
                    line=line,
                    retired_surface=old_name,
                    matched=m.group(0),
                    suggested=renamed_tool_suggestion(old_name),
                    host_permission=host_perm,
                    renderer_provenance=_provenance_flag(m),
                )
            )
    findings.sort(key=lambda f: (f.file, f.line, f.retired_surface))
    return findings


def scan_repo_channels(
    root: Path | str,
) -> tuple[list[StaleReference], list[StaleReference], list[StaleReference]]:
    """Scan ``root`` and partition findings into the THREE channels.

    Returns ``(reconciliation, host_permission_flags, renderer_provenance_flags)``:

    * ``reconciliation`` — stale refs in editable repo docs/prompts/configs/scripts. The agent applies
      each suggested edit itself.
    * ``host_permission_flags`` — stale refs in host permission/allow-rule files
      (``HOST_PERMISSION_FILES``) OUTSIDE the permissions renderer's provenance. The agent CANNOT
      self-edit these under host auto-mode guards, so they are flagged for the operator to edit
      (seed-160 "flagged separately for the operator"). All of ``.claude/settings.local.json`` and
      ``.cursor/settings.json``, and every non-provenance ``.claude/settings.json`` hit, stay here.
    * ``renderer_provenance_flags`` (wave 1u2az): stale allow rules in ``.claude/settings.json``
      recorded in the permissions renderer's provenance: SELF-HEALING; the next upgrade/install
      permissions render prunes/replaces them; nobody hand-edits these.

    All lists hold :class:`StaleReference` in the same deterministic (file, line, retired_surface)
    order produced by :func:`scan_repo`.
    """
    reconciliation: list[StaleReference] = []
    host_permission_flags: list[StaleReference] = []
    renderer_provenance_flags: list[StaleReference] = []
    for ref in scan_repo(root):
        if ref.renderer_provenance:
            renderer_provenance_flags.append(ref)
        elif ref.host_permission:
            host_permission_flags.append(ref)
        else:
            reconciliation.append(ref)
    return reconciliation, host_permission_flags, renderer_provenance_flags

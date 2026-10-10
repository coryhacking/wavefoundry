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

import hashlib
import json
import re
import os
import stat
import time
from bisect import bisect_right
from contextlib import contextmanager
import contained_files
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath
from typing import Iterator

# ── The one shared retired→new map ────────────────────────────────────────────
# Imported, never re-authored. ``_RETIRED_SURFACE_REPLACEMENTS`` is co-located with
# ``_RETIRED_BIN_WRAPPERS`` in render_platform_surfaces.py; ``retired_surface_suggestion`` resolves
# the human-facing replacement form (``wf <subcommand>`` or the no-replacement guidance).
import record_paths  # noqa: E402  record roots (wave 1y0gz)
import vocabulary_profile  # noqa: E402  lifecycle prompt names (wave 1zyb4)
from history_paths import is_history_path  # noqa: E402  shared history components (wave 1zyb2)
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

# ── Retired CONTENT references (wave 1v4mv) ──────────────────────────────────
# A THIRD family, and it exists because the two above cannot express what it
# matches. Both of those find a NAME inside a known literal shape
# (`.wavefoundry/bin/<name>`, `mcp__wavefoundry__<tool>`), so retiring a
# subsystem cannot be expressed by adding an entry to the shared map: that
# would only make the scan look for `.wavefoundry/bin/journal`. A retired
# SUBSYSTEM leaves behind prose instructions and directory paths, which is what
# these patterns match. Same scan, same report-only contract, same findings
# shape — no second scanner.
#
# Each entry is (pattern, retired_surface label, suggestion). Patterns are
# ANCHORED to the retired system's own distinctive vocabulary rather than the
# bare word "journal": prose may legitimately narrate history, and a scan that
# fires on that trains operators to ignore the channel.
_JOURNAL_SUGGESTION = (
    "the journal system is retired; capture durable lessons as typed memory "
    "records under docs/agents/memory/ (memory_add / memory_propose)"
)

# `Distill journals` is ALSO the documented legacy alias of the LIVE `Migrate
# journals` command (seed-210), so the phrase is stale as a closure instruction
# and correct as an alias entry. Found by running the scan against this
# repository: `AGENTS.md` names the alias in its shortcut table, and flagging it
# would tell operators to delete a working command's alias. The guard is
# line-scoped and names the live command, so it cannot silence a bare
# instruction that merely appears near one.
_LIVE_JOURNAL_MIGRATION = re.compile(r"(?i)migrate journals|210-migrate-journals")

# (pattern, retired_surface label, suggestion, line-scoped exemption or None)
_RETIRED_CONTENT_PATTERNS: tuple[
    tuple[re.Pattern[str], str, str, re.Pattern[str] | None], ...
] = (
    # The retired directory itself, including the placeholder forms docs use
    # (`docs/agents/journals/<slug>.md`, `docs/agents/journals/**`).
    (
        re.compile(r"docs/agents/journals(?:/[\w.<>*-]*)*"),
        "docs/agents/journals",
        _JOURNAL_SUGGESTION,
        _LIVE_JOURNAL_MIGRATION,
    ),
    # Instruction shapes reported from the field. Each is a directive telling an
    # agent to write into the retired system, not a historical mention.
    (
        re.compile(r"(?i)stop and journal when\s*:?"),
        "journal instruction",
        _JOURNAL_SUGGESTION,
        None,
    ),
    (
        re.compile(r"(?i)distill journals?\b"),
        "journal instruction",
        _JOURNAL_SUGGESTION,
        _LIVE_JOURNAL_MIGRATION,
    ),
    (
        re.compile(r"(?i)associated journal\b"),
        "journal instruction",
        _JOURNAL_SUGGESTION,
        None,
    ),
    (
        re.compile(r"(?i)memory responsibility\s*:\s*journal"),
        "journal instruction",
        _JOURNAL_SUGGESTION,
        None,
    ),
)

# ── Retired plan-review identity (wave 1w047) ────────────────────────────────
#
# The conversational phrases remain supported aliases.  Only the old HOST
# SKILL name and old prompt/seed paths are retired, so these patterns stay
# deliberately literal and case-sensitive.  Each entry is
# (pattern, retired_surface label, suggested replacement).
_RETIRED_PLAN_REVIEW_AGENT_PROMPT = (
    "docs/prompts/agents/interrogate-plan.prompt.md"
)
_RETIRED_PLAN_REVIEW_AGENT_PROMPT_SUGGESTION = (
    "merge unique guidance into docs/prompts/review-plan.prompt.md, then remove "
    "the obsolete agents prompt"
)
_RETIRED_PLAN_REVIEW_PATTERNS: tuple[
    tuple[re.Pattern[str], str, str], ...
] = (
    (
        re.compile(r"(?<![\w-])wf\-interrogate\-plan(?![\w-])"),
        "wf-interrogate-plan",
        "wf-review-plan",
    ),
    (
        re.compile(
            r"(?<![\w.-])docs/prompts/interrogate\-plan\.prompt\.md(?![\w.-])"
        ),
        "docs/prompts/interrogate-plan.prompt.md",
        "docs/prompts/review-plan.prompt.md",
    ),
    (
        re.compile(
            r"(?<![\w.-])docs/prompts/agents/interrogate\-plan\.prompt\.md(?![\w.-])"
        ),
        _RETIRED_PLAN_REVIEW_AGENT_PROMPT,
        _RETIRED_PLAN_REVIEW_AGENT_PROMPT_SUGGESTION,
    ),
    (
        re.compile(
            r"(?<![\w.-])(?:\.wavefoundry/framework/seeds/)?"
            r"175\-interrogate\-plan\.prompt\.md(?![\w.-])"
        ),
        "175-interrogate-plan.prompt.md",
        ".wavefoundry/framework/seeds/175-review-plan.prompt.md",
    ),
)


# ── Retired feature-named lifecycle prompts (wave 1zyc5) ─────────────────────
#
# Plan feature and Implement feature were renamed to Plan change and Implement
# change (the renderer moves the two prompt pairs byte-for-byte); Finalize
# feature was retired in favor of Close change and Close wave. The finalize
# prompts are project-owned and possibly customized, so they are reported by
# file identity and never deleted automatically. Phrase entries match only the
# shortcut-shaped forms (bold or backticked), so ordinary prose such as
# "Implement feature flags" is never flagged. All entries are case-sensitive.
_RETIRED_FINALIZE_PROMPTS: tuple[str, ...] = (
    "docs/prompts/finalize-feature.prompt.md",
    "docs/prompts/agents/finalize-feature.prompt.md",
)
# Wave 1zyb4 (1zxnw): the replacement side (suggestions) follows the
# vocabulary profile; the retired names matched below stay literal.
_RETIRED_FINALIZE_PROMPT_SUGGESTION = (
    f"merge unique guidance into {vocabulary_profile.prompt_doc('close-wave')} or "
    f"{vocabulary_profile.prompt_doc('close-change')}, then remove the retired prompt"
)
_CLOSE_CHANGE_OR_WAVE_SUGGESTION = (
    f"{vocabulary_profile.shortcut('close-change')} (one change) or "
    f"{vocabulary_profile.shortcut('close-wave')} (the wave)"
)


def _shortcut_phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase)
    return re.compile(rf"\*\*{escaped}\*\*|`{escaped}`")


_RETIRED_CHANGE_PROMPT_PATTERNS: tuple[
    tuple[re.Pattern[str], str, str], ...
] = (
    (
        re.compile(r"(?<![\w-])wf\-plan\-feature(?![\w-])"),
        "wf-plan-feature",
        vocabulary_profile.skill_name("plan-change"),
    ),
    *(
        (
            re.compile(
                rf"(?<![\w.-])docs/prompts/{agents}{verb}\-feature\.prompt\.md(?![\w.-])"
            ),
            f"docs/prompts/{agents}{verb}-feature.prompt.md",
            f"docs/prompts/{agents}{slug}.prompt.md",
        )
        for agents in ("", "agents/")
        # Literal keys (200ew): a distribution's literal-key census sees both.
        for verb, slug in (
            ("plan", vocabulary_profile.prompt_slug("plan-change")),
            ("implement", vocabulary_profile.prompt_slug("implement-change")),
        )
    ),
    (
        re.compile(
            r"(?<![\w.-])(?:\.wavefoundry/framework/seeds/)?"
            r"170\-plan\-feature\.prompt\.md(?![\w.-])"
        ),
        "170-plan-feature.prompt.md",
        ".wavefoundry/framework/seeds/170-plan-change.prompt.md",
    ),
    (
        re.compile(
            r"(?<![\w.-])(?:\.wavefoundry/framework/seeds/)?"
            r"180\-implement\-feature\.prompt\.md(?![\w.-])"
        ),
        "180-implement-feature.prompt.md",
        ".wavefoundry/framework/seeds/180-implement-change.prompt.md",
    ),
    (
        re.compile(
            r"(?<![\w.-])(?:\.wavefoundry/framework/seeds/)?"
            r"190\-finalize\-feature\.prompt\.md(?![\w.-])"
        ),
        "190-finalize-feature.prompt.md",
        ".wavefoundry/framework/seeds/190-close-wave.prompt.md",
    ),
    (_shortcut_phrase_pattern("Plan feature"), "Plan feature", vocabulary_profile.shortcut("plan-change")),
    (
        _shortcut_phrase_pattern("Implement feature"),
        "Implement feature",
        vocabulary_profile.shortcut("implement-change"),
    ),
    (
        _shortcut_phrase_pattern("Finalize feature"),
        "Finalize feature",
        _CLOSE_CHANGE_OR_WAVE_SUGGESTION,
    ),
)

# The renderer refreshes only the BODY of the Claude guru agent and keeps its
# existing frontmatter verbatim, so a target's ``description:`` line keeps the
# retired bare phrase after upgrade. Matched only on that frontmatter line.
_CLAUDE_GURU_AGENT_FILE = ".claude/agents/guru.md"
_GURU_DESCRIPTION_RETIRED_PHRASE = re.compile(r"(?<![\w-])Plan feature(?![\w-])")


def _guru_description_hits(rel: str, text: str) -> Iterator[tuple[int, str]]:
    """Yield ``(offset, matched)`` for the retired phrase on the guru agent's
    frontmatter ``description:`` line."""
    if rel != _CLAUDE_GURU_AGENT_FILE or not text.startswith("---"):
        return
    end = text.find("\n---", 3)
    if end < 0:
        return
    offset = 0
    for line in text[:end].split("\n"):
        if line.lstrip().startswith("description:"):
            for m in _GURU_DESCRIPTION_RETIRED_PHRASE.finditer(line):
                yield offset + m.start(), m.group(0)
        offset += len(line) + 1

# ── Profile-renamed lifecycle prompts (wave 1zyb4, change 1zxnw) ─────────────
#
# Under a vocabulary profile that renames a tier-named lifecycle prompt, each
# renamed key's default public path, agent path, skill name, and shortcut-shaped
# shortcut and alias phrases (bold or backticked) are reported with the
# profile's name (an alias with the key's current shortcut), and the bare
# phrases on the guru agent's ``description:`` line too. A default token that
# equals any current derived token (a chain reuses it) is never reported.
# Under the default profile the table is empty.
def _profile_prompt_name_tables() -> "tuple[tuple[tuple[re.Pattern[str], str, str], ...], tuple[tuple[re.Pattern[str], str, str], ...]]":
    names = vocabulary_profile.PROMPT_NAMES
    defaults = vocabulary_profile.DEFAULT_PROMPT_NAMES
    current = set()
    for key in names:
        current.update({
            vocabulary_profile.prompt_doc(key), vocabulary_profile.agent_prompt_doc(key),
            vocabulary_profile.skill_name(key), vocabulary_profile.shortcut(key),
        })
        # A live alias (e.g. a profile keeping a default phrase as an alias)
        # is current, never retired.
        current.update(vocabulary_profile.shortcut_aliases(key))
    patterns: list[tuple[re.Pattern[str], str, str]] = []
    guru: list[tuple[re.Pattern[str], str, str]] = []
    for key, default in defaults.items():
        if names[key] == default:
            continue
        slug = default["slug"]
        candidates = (
            (f"docs/prompts/{slug}.prompt.md", vocabulary_profile.prompt_doc(key), "path"),
            (f"docs/prompts/agents/{slug}.prompt.md", vocabulary_profile.agent_prompt_doc(key), "path"),
            (f"wf-{slug}", vocabulary_profile.skill_name(key), "skill"),
            (default["shortcut"], vocabulary_profile.shortcut(key), "phrase"),
            # Wave 200xy (200xx): each default alias suggests the current shortcut.
            *((alias, vocabulary_profile.shortcut(key), "phrase") for alias in default["aliases"]),
        )
        for token, suggestion, kind in candidates:
            if token in current or token == suggestion:
                continue
            escaped = re.escape(token)
            if kind == "path":
                # A sentence-ending period is not part of the path.
                pattern = re.compile(rf"(?<![\w.-]){escaped}(?![\w-]|\.\w)")
            elif kind == "skill":
                pattern = re.compile(rf"(?<![\w-]){escaped}(?![\w-])")
            else:
                pattern = _shortcut_phrase_pattern(token)
                guru.append((re.compile(rf"(?<![\w-]){escaped}(?![\w-])"), token, suggestion))
            patterns.append((pattern, token, suggestion))
    return tuple(patterns), tuple(guru)


_PROFILE_PROMPT_NAME_PATTERNS, _PROFILE_GURU_DESCRIPTION_PHRASES = _profile_prompt_name_tables()


def _guru_description_lines(rel: str, text: str) -> Iterator[tuple[int, str]]:
    """Yield ``(offset, line)`` for the guru agent's frontmatter ``description:`` line."""
    if rel != _CLAUDE_GURU_AGENT_FILE or not text.startswith("---"):
        return
    end = text.find("\n---", 3)
    if end < 0:
        return
    offset = 0
    for line in text[:end].split("\n"):
        if line.lstrip().startswith("description:"):
            yield offset, line
        offset += len(line) + 1


def _line_text(text: str, position: int) -> str:
    """Return the full line containing *position* (for line-scoped exemptions)."""
    start = text.rfind("\n", 0, position) + 1
    end = text.find("\n", position)
    return text[start:] if end < 0 else text[start:end]

# The `.md` to `.prompt.md` rename. Unlike every pattern above, this one cannot
# be decided from the matched text alone: `docs/prompts/foo.md` is stale only
# when `docs/prompts/foo.prompt.md` exists on disk. The resolver below performs
# that check, so a reference to a genuinely-`.md` prompt file is never flagged.
# The trailing guard is `(?!\w)`, NOT `(?![\w.])`. A sentence-ending period is
# the single most common thing to follow a reference in prose, and excluding it
# silently dropped the last reference on a line — the exact under-count AC-4
# exists to prevent. Caught by the AC-4 fixture, not by inspection.
_PROMPT_MD_REFERENCE = re.compile(r"(?<![\w.-])([\w./-]*docs/prompts/[\w.-]+?)\.md(?!\w)")
_PROMPT_EXTENSION_SUGGESTION = (
    "prompt files carry the .prompt.md extension; update the reference to {new}"
)


def _stale_prompt_extension_hits(
    root: Path, text: str, *, work=None
) -> Iterator[tuple[re.Match[str], str, str]]:
    """Yield ``(match, matched_text, suggestion)`` for each stale prompt reference.

    Resolution-based, not textual: a hit requires the ``.prompt.md`` twin to
    exist under *root*. That keeps the pattern silent on prompt-adjacent docs
    that legitimately end in ``.md`` and on a reference that is already correct.
    """
    cursor = 0
    while True:
        anchor = text.find("docs/prompts/", cursor)
        if anchor < 0:
            return
        cursor = anchor + len("docs/prompts/")
        if work is not None:
            work.candidate()
        start = anchor
        while start > 0 and anchor - start < MAX_PROMPT_TOKEN and (text[start - 1].isalnum() or text[start - 1] in "_./-"):
            start -= 1
        end = cursor
        while end < len(text) and end - start < MAX_PROMPT_TOKEN and (text[end].isalnum() or text[end] in "_.-"):
            end += 1
        if (start > 0 and (text[start - 1].isalnum() or text[start - 1] in "_.-")) or end - start >= MAX_PROMPT_TOKEN:
            if work is not None:
                work.omit("prompt_token")
            continue
        match = _PROMPT_MD_REFERENCE.match(text, start, end)
        if match is None:
            continue
        stem = match.group(1)
        if stem.endswith(".prompt"):
            continue
        index = stem.find("docs/prompts/")
        rooted = stem[index:] if index >= 0 else stem
        twin = root / f"{rooted}.prompt.md"
        try:
            info = twin.lstat()
        except OSError:
            continue
        if not stat.S_ISREG(info.st_mode) or twin.is_symlink():
            continue
        yield match, match.group(0), _PROMPT_EXTENSION_SUGGESTION.format(new=f"{rooted}.prompt.md")


# ── Exclusion set ─────────────────────────────────────────────────────────────
# Directory exclusions matched on path COMPONENT/PREFIX (NOT raw substring) — mirrors
# ``build_pack.should_exclude`` (``rel == d or rel.startswith(d + "/")``). Raw substring matching
# over-excludes in-scope operator docs: e.g. `docs/reports-overview.md` is NOT under `docs/reports/`,
# and a substring check would wrongly drop it. The framework pack tree, generated index, wave/report
# history, and vcs/build dirs are excluded; ``docs/reports`` is the change doc's added history root.
_STATIC_EXCLUDED_DIRS: tuple[str, ...] = (
    ".git",
    "__pycache__",
    "node_modules",
    ".wavefoundry/framework",  # the framework pack tree — its own source legitimately names them
    ".wavefoundry/index",      # generated/runtime semantic index artifacts
    ".wavefoundry/cache",      # runtime caches, including the bytecode cache (change 1zyv1)
    ".wavefoundry/upgrade-assets",  # retained protocol-bridge payload/recovery artifacts
    "docs/reports",            # report history
    "docs/agents/memory",      # memory records quote history; the memory corpus has its own hygiene loop
    "docs/agents/history",     # dated operating-memory snapshots (wave 1zyc5)
)
# Wave 1y0gz: the wave history root comes from the resolved record layout.
# ``excluded_dirs_for(root)`` resolves it for the scan walk; wave 1z8ty removed
# the import-time default-layout set so no default is captured at import.


def excluded_dirs_for(root: Path) -> tuple[str, ...]:
    """The exclusion set with the wave history root, and the read-only archive
    root when set (wave 1z8ts), resolved for ``root``."""
    roots = record_paths.load_record_roots(root)
    archive = (roots.archive_rel,) if roots.archive_rel else ()
    return _STATIC_EXCLUDED_DIRS + (roots.waves_rel,) + archive
# Protocol-bridge upgrades retain the previous framework tree under a generated sibling such as
# ``.wavefoundry/framework.rollback-bridge-pfps-p2/``.  It is inactive recovery state, not a live
# project carrier.  Keep this separate from ``excluded_dirs_for`` because it is a component prefix, not
# one fixed directory name.
_FRAMEWORK_ROLLBACK_DIR_PREFIX = "framework.rollback-"
# File-name exclusions matched on BASENAME anywhere in the tree (not root-only). A file named
# `CHANGELOG.md` is release history wherever it lives (e.g. a nested `.wavefoundry/CHANGELOG.md`), and
# `prompt-surface-manifest.json` is a renderer-managed generated manifest whose historical
# `upgrade_merge_notes` cause false positives — like the generated index, it is not operator-authored.
# 1v7a1 adds the disposition store. It RECORDS the matched text of each settled
# finding, so without this exclusion the act of dispositioning a finding creates
# a new finding quoting it — self-defeating, and caught by the AC-1 fixture
# rather than by inspection. Machine-managed like its two siblings here, never
# operator prose.
EXCLUDED_BASENAMES: tuple[str, ...] = (
    "CHANGELOG.md",
    "prompt-surface-manifest.json",
    "reconcile-dispositions.json",
)

# History directories are matched on a path COMPONENT (not substring) through the shared
# ``history_paths`` predicate (wave 1zyb2, 1zxnt): a file *under* a history directory is history.
# This does not drop `src/snapshotter.py` (substring `snapshot`) or a doc whose name merely
# contains `journal`.

# ── Framework-mandated archive sections (wave 1vk4c / 1vk4b) ────────────────
# seed-230 §6 tells the agent to MOVE a resolved `docs/missing-docs.md` row into
# a `## Resolved / closed` table with a dated resolution note. When the resolved
# component is a later-retired surface, that note necessarily names it, and the
# row is exactly the historical record seed-160/220 protect ("retiring a file
# removes the file, not the historical record of it"), so reporting it recurred
# on every consumer upgrade (field feedback, 1.17.1). This exclusion is
# STRUCTURAL, like the path exclusions above (applied in `scan_repo` beside
# `is_excluded`), not a judgment (dispositions stay at the channel boundary).
# Exact allowlist of (repo-relative POSIX path, ATX H2 heading text, case-folded);
# grow it only when a seed prescribes another archive heading, never widen it to
# a heuristic. Only TABLE ROWS under the heading are exempt (seed-230 mandates a
# table); prose parked under it still reports.
_ARCHIVE_SECTIONS: tuple[tuple[str, str], ...] = (
    ("docs/missing-docs.md", "resolved / closed"),
)
# ATX heading: 0-3 leading spaces, 1-6 hashes, then either end-of-line (an EMPTY
# heading, which still terminates a span) or at least one space/tab plus text and
# optional closing hashes. `##Resolved` (no space) and setext underlines are NOT
# headings here, so they can never open an exempt span (fail toward reporting).
_ATX_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t#]*$")
# Code fence: 0-3 leading spaces and a run of 3+ backticks or tildes. Per CommonMark
# a fence closes only on the SAME character with a run at least as long as the
# opener, so a ``` line inside a ```` block does not close it and a `~~~` line
# inside a ``` block is content.
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def _archive_row_spans(text: str, rel: str) -> list[tuple[int, int]]:
    """``(start, end)`` offsets of table rows inside an allowlisted archive section.

    Returns ``[]`` unless *rel* is allowlisted AND the text carries the exact ATX
    H2 heading outside a code fence. A span runs from that heading to the next
    ATX H1/H2 (nested H3+ stays inside) or EOF; only lines whose first non-space
    character is ``|`` contribute. ``\r`` is stripped so CRLF files behave.
    """

    wanted = {heading for path, heading in _ARCHIVE_SECTIONS if path == rel}
    if not wanted:
        return []
    spans: list[tuple[int, int]] = []
    active = False
    fence: tuple[str, int] | None = None  # (fence char, opener length)
    offset = 0
    for line in text.splitlines(keepends=True):
        start = offset
        offset += len(line)
        raw = line.rstrip("\r\n")
        fence_match = _FENCE_RE.match(raw)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = (marker[0], len(marker))
                continue
            tail = raw[fence_match.end(1):]
            if (
                marker[0] == fence[0]
                and len(marker) >= fence[1]
                and not tail.strip()
            ):
                fence = None
                continue
            # a shorter or other-character run inside an open fence is content
        if fence is not None:
            continue
        heading = _ATX_HEADING_RE.match(raw)
        if heading:
            if len(heading.group(1)) <= 2:
                active = (
                    len(heading.group(1)) == 2
                    and (heading.group(2) or "").strip().casefold() in wanted
                )
            continue
        if active and raw.lstrip().startswith("|"):
            spans.append((start, start + len(raw)))
    return spans


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
    logical_line: str = ""
    heading_context: str = ""
    disposition_state: str = "unrecorded"

    def as_dict(self) -> dict[str, object]:
        return {
            "file": self.file,
            "line": self.line,
            "retired_surface": self.retired_surface,
            "matched": self.matched,
            "suggested": self.suggested,
            "disposition_key": disposition_key(self),
            "disposition_key_version": "v2",
            "legacy_disposition_key": legacy_disposition_key(self),
            "disposition_state": self.disposition_state,
            "logical_line": self.logical_line,
            "heading_context": self.heading_context,
            "proposed_v2_key": (
                disposition_key(self)
                if self.disposition_state.startswith("legacy-")
                else None
            ),
        }


def _finding_context(text: str, line_number: int) -> tuple[str, str]:
    """Return ``(logical line, preceding ATX heading)`` for a 1-based line.

    Heading capture reuses the scanner's CommonMark-style fence rules. The
    complete heading line is retained; headings inside fences never become
    context. Physical line terminators are excluded from both fields.
    """

    lines = text.splitlines()
    if not lines:
        return "", ""
    target_index = min(max(line_number, 1), len(lines)) - 1
    heading_context = ""
    fence: tuple[str, int] | None = None
    for raw in lines[:target_index]:
        fence_match = _FENCE_RE.match(raw)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = (marker[0], len(marker))
                continue
            tail = raw[fence_match.end(1):]
            if (
                marker[0] == fence[0]
                and len(marker) >= fence[1]
                and not tail.strip()
            ):
                fence = None
                continue
        if fence is not None:
            continue
        if _ATX_HEADING_RE.match(raw):
            heading_context = raw
    return lines[target_index], heading_context


def is_excluded(
    rel: str, *, name: str, suffix: str, excluded_dirs: tuple[str, ...]
) -> bool:
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
    for d in excluded_dirs:
        if rel == d or rel.startswith(d + "/"):
            return True
        if "/" not in d and d in parts:
            return True
    # File-name exclusions matched by BASENAME anywhere: CHANGELOG.md is release history wherever it
    # lives (incl. a nested `.wavefoundry/CHANGELOG.md`); prompt-surface-manifest.json is a generated,
    # renderer-managed manifest whose historical upgrade_merge_notes are not operator-authored refs.
    if name in EXCLUDED_BASENAMES:
        return True
    # History directories, matched on a component of the repo-relative path, not a substring.
    # ``rel`` is POSIX-spelled and root-relative, so it is passed as a PurePosixPath: a POSIX
    # path is anchored only by ``/``, and a repository file named like ``c:notes.md`` is a
    # plain name here, not a Windows drive that would make the helper refuse the scan.
    if is_history_path(PurePosixPath(rel)):
        return True
    # Test files name the retired surfaces to assert they are gone (a `tests/` component + `test_`
    # filename), anywhere in the tree — not just the framework tests dir.
    if "tests" in parts and name.startswith("test_"):
        return True
    return False


DEFAULT_SCAN_ENTRIES = 100_000
DEFAULT_SCAN_FILES = 10_000
DEFAULT_SCAN_FILE_BYTES = 16 * 1024 * 1024
DEFAULT_SCAN_TOTAL_BYTES = 128 * 1024 * 1024
DEFAULT_SCAN_CANDIDATES = 100_000
DEFAULT_SCAN_FINDINGS = 10_000
DEFAULT_SCAN_SECONDS = 30.0
MAX_PROMPT_TOKEN = 4096
MAX_CONTEXT_CHARS = 4096


@dataclass(frozen=True)
class ScanLimits:
    entries: int = DEFAULT_SCAN_ENTRIES
    files: int = DEFAULT_SCAN_FILES
    file_bytes: int = DEFAULT_SCAN_FILE_BYTES
    total_bytes: int = DEFAULT_SCAN_TOTAL_BYTES
    candidates: int = DEFAULT_SCAN_CANDIDATES
    findings: int = DEFAULT_SCAN_FINDINGS
    seconds: float = DEFAULT_SCAN_SECONDS


@dataclass
class ScanResult:
    state: str = "complete"
    reasons: list[str] = field(default_factory=list)
    findings: list[StaleReference] = field(default_factory=list)
    reconciliation: list[StaleReference] = field(default_factory=list)
    host_permission_flags: list[StaleReference] = field(default_factory=list)
    renderer_provenance_flags: list[StaleReference] = field(default_factory=list)
    visited_entries: int = 0
    eligible_files: int = 0
    read_files: int = 0
    read_bytes: int = 0
    candidates: int = 0
    elapsed: float = 0.0
    last_path: str = ""
    last_stage: str = "start"

    def as_dict(self) -> dict:
        return {**{key: value for key, value in vars(self).items()
                   if key not in ("findings", "reconciliation", "host_permission_flags", "renderer_provenance_flags")},
                **{key: [ref.as_dict() for ref in getattr(self, key)] for key in
                   ("reconciliation", "host_permission_flags", "renderer_provenance_flags")}}


class ScanIncomplete(RuntimeError):
    """Legacy shapes cannot represent partial work; carry the truthful result."""
    def __init__(self, result: ScanResult):
        self.result = result
        super().__init__("reconciliation scan " + result.state + ": " + ",".join(result.reasons))


class _ScanStop(Exception):
    pass


class _ScanWork:
    def __init__(self, limits, progress=None):
        self.limits = limits
        self.result = ScanResult()
        self.started = time.monotonic()
        self.progress = progress

    def omit(self, reason, *, error=False):
        if reason not in self.result.reasons:
            self.result.reasons.append(reason)
        if error or self.result.state != "error":
            self.result.state = "error" if error else "incomplete"

    def checkpoint(self, stage, rel=None):
        if rel is not None:
            self.result.last_path = rel[:160]
        self.result.last_stage = stage
        self.result.elapsed = time.monotonic() - self.started
        if self.progress:
            self.progress({key: getattr(self.result, key) for key in
                           ("last_path", "last_stage", "elapsed", "visited_entries", "eligible_files", "read_files", "read_bytes", "candidates")})
        if self.result.elapsed >= self.limits.seconds:
            self.omit("deadline")
            raise _ScanStop()

    def candidate(self):
        self.checkpoint("candidate")
        if self.result.candidates >= self.limits.candidates:
            self.omit("candidates")
            raise _ScanStop()
        self.result.candidates += 1

    def matches(self, pattern, text):
        self.checkpoint("pattern")
        for match in pattern.finditer(text):
            self.candidate()
            yield match
        self.checkpoint("pattern_done")

    def read(self, root, path, rel):
        self.checkpoint("read", rel)
        # contained_files intentionally supports contained links; this scanner
        # additionally refuses every lexical link, including Windows junctions.
        cursor = root
        for part in Path(rel).parts:
            cursor = cursor / part
            info = cursor.lstat()
            if stat.S_ISLNK(info.st_mode) or contained_files._is_windows_link(str(cursor)):
                self.omit("link_refused")
                return None
        if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1:
            self.omit("special_file_refused")
            return None
        if info.st_size > self.limits.file_bytes:
            self.omit("file_bytes")
            return None
        remaining = self.limits.total_bytes - self.result.read_bytes
        if info.st_size > remaining:
            self.omit("total_bytes")
            raise _ScanStop()
        cap = min(self.limits.file_bytes, max(0, remaining))
        if contained_files._dir_fd_supported():
            parent_fd = contained_files.open_contained_dir(root, Path(rel).parts[:-1])
            try:
                fd = os.open(Path(rel).name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0), dir_fd=parent_fd)
                try:
                    opened = os.fstat(fd)
                    if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                        self.omit("read_changed")
                        return None
                    chunks = []
                    size = 0
                    allowance = min(cap + 1, remaining)
                    while size < allowance:
                        self.checkpoint("read_chunk")
                        block = os.read(fd, min(65536, allowance - size))
                        if not block:
                            break
                        chunks.append(block)
                        size += len(block)
                        self.result.read_bytes += len(block)
                    data = b"".join(chunks)
                    if size == allowance and os.fstat(fd).st_size > size:
                        self.omit("total_bytes" if allowance == remaining else "file_bytes")
                        return None
                finally:
                    os.close(fd)
            finally:
                os.close(parent_fd)
        else:
            # Native Windows has no dir_fd/O_NOFOLLOW; contained_files verifies
            # the opened identity. Lexical pre/post checks retain its documented
            # component-swap window, without accepting a known lexical link.
            data, opened, resolved = contained_files.read_contained_identity(root, path, max_bytes=cap)
            self.result.read_bytes += len(data)
            if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino) or resolved != root.resolve().joinpath(*Path(rel).parts):
                self.omit("read_changed")
                return None
        if len(data) > cap:
            self.omit("file_bytes" if cap == self.limits.file_bytes else "total_bytes")
            if cap < self.limits.file_bytes:
                raise _ScanStop()
            return None
        self.result.read_files += 1
        self.checkpoint("read_done")
        return data.decode("utf-8")



class _FileFindings(list):
    def __init__(self, work):
        super().__init__()
        self.work = work

    def append(self, ref):
        if len(self.work.result.findings) + len(self) >= self.work.limits.findings:
            self.work.omit("findings")
            raise _ScanStop()
        super().append(ref)


def _directory_excluded(rel, excluded_dirs, *, directory=False):
    parts = rel.split("/")
    if parts[0] in (".local", "target"):
        return True
    if (len(parts) >= 3 or directory) and len(parts) >= 2 and parts[0] == ".wavefoundry" and parts[1].startswith(_FRAMEWORK_ROLLBACK_DIR_PREFIX):
        return True
    return is_history_path(PurePosixPath(rel)) or any(
        rel == d or rel.startswith(d + "/") or ("/" not in d and d in parts)
        for d in excluded_dirs)


@contextmanager
def _scan_directory(root, directory):
    if contained_files._dir_fd_supported():
        fd = contained_files.open_contained_dir(root, directory.relative_to(root).parts)
        try:
            with os.scandir(fd) as entries:
                yield entries
        finally:
            os.close(fd)
    else:
        # Native Windows has the documented component-swap window; reads
        # still perform contained identity checks and refuse known links.
        with os.scandir(directory) as entries:
            yield entries


def _iter_scannable_files(root: Path, work=None) -> Iterator[tuple[Path, str]]:
    work = work or _ScanWork(ScanLimits())
    excluded_dirs = excluded_dirs_for(root)
    stack = [root]
    while stack:
        directory = stack.pop()
        work.checkpoint("directory", directory.relative_to(root).as_posix())
        try:
            with _scan_directory(root, directory) as entries:
                for entry in entries:
                    work.checkpoint("entry")
                    if work.result.visited_entries >= work.limits.entries:
                        work.omit("entries")
                        raise _ScanStop()
                    work.result.visited_entries += 1
                    path = directory / entry.name
                    rel = path.relative_to(root).as_posix()
                    if _directory_excluded(rel, excluded_dirs, directory=entry.is_dir(follow_symlinks=False)):
                        continue
                    if entry.is_dir(follow_symlinks=False) and not contained_files._is_windows_link(str(path)):
                        stack.append(path)
                        continue
                    if is_excluded(rel, name=path.name, suffix=path.suffix, excluded_dirs=excluded_dirs):
                        continue
                    if work.result.eligible_files >= work.limits.files:
                        work.omit("files")
                        raise _ScanStop()
                    work.result.eligible_files += 1
                    yield path, rel
        except OSError as exc:
            work.omit("traversal_" + type(exc).__name__, error=True)


def _contextualize_file(findings, text, work):
    # One pass per file, retaining only context for lines with findings. Both
    # fence consumers use the same strict whitespace-only closing predicate.
    wanted = {ref.line for ref in findings}
    if not wanted:
        return []
    contexts = {}
    heading = ""
    fence = None
    for number, raw in enumerate(text.splitlines(), 1):
        try:
            work.checkpoint("context")
        except _ScanStop:
            break
        if number in wanted:
            if len(raw) > MAX_CONTEXT_CHARS or len(heading) > MAX_CONTEXT_CHARS:
                work.omit("context_bytes")
            contexts[number] = (raw[:MAX_CONTEXT_CHARS], heading[:MAX_CONTEXT_CHARS])
        match = _FENCE_RE.match(raw)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = (marker[0], len(marker))
                continue
            if marker[0] == fence[0] and len(marker) >= fence[1] and not raw[match.end(1):].strip():
                fence = None
                continue
        if fence is None and _ATX_HEADING_RE.match(raw):
            heading = raw
    return [replace(ref, logical_line=contexts.get(ref.line, ("", ""))[0],
                    heading_context=contexts.get(ref.line, ("", ""))[1]) for ref in findings]


def _scan_file(root, path, rel, text, work, findings):
    provenance = frozenset()
    if rel == _CLAUDE_SETTINGS_FILE:
        try:
            loaded = json.loads(text)
            raw = loaded.get(PERMISSIONS_PROVENANCE_KEY) if isinstance(loaded, dict) else None
            if isinstance(raw, list):
                provenance = frozenset(item for item in raw if isinstance(item, str))
        except ValueError:
            pass
    line_starts = [0] + [m.end() for m in re.finditer("\n", text)]
    host_perm = is_host_permission_file(rel)
    # A project-specific agents-layer prompt is a retired carrier by its
    # existence, even when its body never spells its own path. It cannot be
    # migrated safely because its unique guidance is project-owned, so this
    # remains report-only and directs the operator to merge/remove it.
    if rel in _RETIRED_FINALIZE_PROMPTS:
        findings.append(
            StaleReference(
                file=rel,
                line=1,
                retired_surface=rel,
                matched=rel,
                suggested=_RETIRED_FINALIZE_PROMPT_SUGGESTION,
                host_permission=host_perm,
            )
        )
    if rel == _RETIRED_PLAN_REVIEW_AGENT_PROMPT:
        findings.append(
            StaleReference(
                file=rel,
                line=1,
                retired_surface=_RETIRED_PLAN_REVIEW_AGENT_PROMPT,
                matched=rel,
                suggested=_RETIRED_PLAN_REVIEW_AGENT_PROMPT_SUGGESTION,
                host_permission=host_perm,
            )
        )
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

    # Wave 1vk4c: table rows under a framework-mandated archive heading are
    # historical record; every producer below skips a match that starts
    # inside one (empty for every file but the allowlisted archive carriers).
    archive_spans = _archive_row_spans(text, rel)

    def _archived(m: re.Match[str]) -> bool:
        return any(s <= m.start() < e for s, e in archive_spans)

    patterns = [_LITERAL_PATTERN]
    if path.suffix == ".py":
        patterns += [_DYNAMIC_PATTERN, _VAR_BINDIR_PATTERN]
    for pat in patterns:
        for m in work.matches(pat, text):
            if _archived(m):
                continue
            retired = m.group(1)
            line = bisect_right(line_starts, m.start())
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
    # Retired CONTENT references (1v4mv): retired-subsystem paths and the
    # instruction shapes that point at them. Every match is reported, not
    # one per line — a single line legitimately carries several stale
    # references, and per-line reporting would silently under-count.
    for pat, retired, suggestion, exempt in _RETIRED_CONTENT_PATTERNS:
        for m in work.matches(pat, text):
            if _archived(m):
                continue
            if exempt is not None and exempt.search(_line_text(text, m.start())):
                continue
            findings.append(
                StaleReference(
                    file=rel,
                    line=bisect_right(line_starts, m.start()),
                    retired_surface=retired,
                    matched=m.group(0),
                    suggested=suggestion,
                    host_permission=host_perm,
                )
            )
    # Retired plan-review identity (1w047): unlike the two supported
    # natural-language aliases, these exact skill/path forms no longer
    # resolve after the hard skill cutover and are repairable in-place.
    for pat, retired, suggestion in _RETIRED_PLAN_REVIEW_PATTERNS:
        for m in work.matches(pat, text):
            if _archived(m):
                continue
            findings.append(
                StaleReference(
                    file=rel,
                    line=bisect_right(line_starts, m.start()),
                    retired_surface=retired,
                    matched=m.group(0),
                    suggested=suggestion,
                    host_permission=host_perm,
                )
            )
    # Retired feature-named lifecycle prompts (1zyc5): renamed prompt and
    # seed paths, the retired skill, shortcut-shaped phrases, and the
    # preserved guru agent description line.
    for pat, retired, suggestion in _RETIRED_CHANGE_PROMPT_PATTERNS:
        for m in work.matches(pat, text):
            if _archived(m):
                continue
            findings.append(
                StaleReference(
                    file=rel,
                    line=bisect_right(line_starts, m.start()),
                    retired_surface=retired,
                    matched=m.group(0),
                    suggested=suggestion,
                    host_permission=host_perm,
                )
            )
    for position, matched in _guru_description_hits(rel, text):
        findings.append(
            StaleReference(
                file=rel,
                line=bisect_right(line_starts, position),
                retired_surface="Plan feature (guru agent description)",
                matched=matched,
                suggested=vocabulary_profile.shortcut("plan-change"),
                host_permission=host_perm,
            )
        )
    # Profile-renamed lifecycle prompts (1zxnw): empty under the defaults.
    for pat, retired, suggestion in _PROFILE_PROMPT_NAME_PATTERNS:
        for m in work.matches(pat, text):
            if _archived(m):
                continue
            findings.append(
                StaleReference(
                    file=rel,
                    line=bisect_right(line_starts, m.start()),
                    retired_surface=retired,
                    matched=m.group(0),
                    suggested=suggestion,
                    host_permission=host_perm,
                )
            )
    if _PROFILE_GURU_DESCRIPTION_PHRASES:
        for offset, line in _guru_description_lines(rel, text):
            for pat, retired, suggestion in _PROFILE_GURU_DESCRIPTION_PHRASES:
                for m in work.matches(pat, line):
                    findings.append(
                        StaleReference(
                            file=rel,
                            line=bisect_right(line_starts, offset + m.start()),
                            retired_surface=f"{retired} (guru agent description)",
                            matched=m.group(0),
                            suggested=suggestion,
                            host_permission=host_perm,
                        )
                    )
    # The `.md` to `.prompt.md` rename, resolved against the tree.
    for m, matched, suggestion in _stale_prompt_extension_hits(root, text, work=work):
        if _archived(m):
            continue
        findings.append(
            StaleReference(
                file=rel,
                line=bisect_right(line_starts, m.start()),
                retired_surface="prompt .md extension",
                matched=matched,
                suggested=suggestion,
                host_permission=host_perm,
            )
        )
    # Renamed MCP tools (1.14.0): the fully-qualified form first; its match
    # spans are masked so the bare pattern cannot double-report the tool
    # name embedded inside `mcp__wavefoundry__<old>`.
    qualified_spans: list[tuple[int, int]] = []
    for m in work.matches(_TOOL_MCP_PATTERN, text):
        qualified_spans.append(m.span())
        if _archived(m):
            continue
        old_name = m.group(1)
        line = bisect_right(line_starts, m.start())
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
    for m in work.matches(_TOOL_BARE_PATTERN, text):
        if any(s <= m.start() < e for s, e in qualified_spans):
            continue
        if _archived(m):
            continue
        old_name = m.group(1)
        line = bisect_right(line_starts, m.start())
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


def scan_repo_result(root: Path | str, *, limits: ScanLimits | None = None, progress=None) -> ScanResult:
    """Bounded report-only scan; omissions never masquerade as clean absence."""
    root = Path(root)
    work = _ScanWork(limits or ScanLimits(), progress)
    try:
        for path, rel in _iter_scannable_files(root, work):
            file_findings = _FileFindings(work)
            text = None
            try:
                text = work.read(root, path, rel)
                if text is not None:
                    _scan_file(root, path, rel, text, work, file_findings)
            except (OSError, UnicodeError) as exc:
                work.omit("read_" + type(exc).__name__)
            finally:
                if text is not None:
                    work.result.findings.extend(_contextualize_file(file_findings, text, work))
            work.checkpoint("file_done", rel)
        dispositions = load_dispositions(root, work=work)
        work.result.findings.sort(key=lambda ref: (ref.file, ref.line, ref.retired_surface))
        channels = _partition_findings(work.result.findings, dispositions, work=work)
        (work.result.reconciliation, work.result.host_permission_flags,
         work.result.renderer_provenance_flags) = channels
    except _ScanStop:
        pass
    except Exception as exc:
        work.omit("scan_" + type(exc).__name__, error=True)
    work.result.findings.sort(key=lambda ref: (ref.file, ref.line, ref.retired_surface))
    # Also partition retained partial findings; failure to load dispositions
    # keeps them visible instead of suppressing evidence.
    if work.result.state != "complete":
        channels = _partition_findings(work.result.findings, {})
        (work.result.reconciliation, work.result.host_permission_flags,
         work.result.renderer_provenance_flags) = channels
    work.result.elapsed = time.monotonic() - work.started
    return work.result


def scan_repo(root: Path | str, *, limits: ScanLimits | None = None) -> list[StaleReference]:
    result = scan_repo_result(root, limits=limits)
    if result.state != "complete":
        raise ScanIncomplete(result)
    return result.findings


# ── Historical-record dispositions (wave 1v7a1) ──────────────────────────────
# The scan has one disposition today — unresolved — so a finding that is CORRECT
# AS WRITTEN can only be silenced by rewriting the record it reports on. That
# collides with the framework's own seeded policy: seed-160 and seed-220 both
# say "retiring a file removes the file, not the historical record of it". A
# sentence recording that a directory was retired is exactly such a record, and
# today it recurs on every upgrade forever.
#
# Modelled on the secrets scanner's ``docs/scan-findings.json``: a store of
# per-finding judgments a human makes ONCE, persisted, consulted on later runs.
# Same idiom deliberately — two differently-shaped disposition stores is how one
# rule becomes two implementations.
DISPOSITIONS_REL = "docs/reconcile-dispositions.json"
HISTORICAL_RECORD = "historical-record"
_V1_KEY_RE = re.compile(r"^[0-9a-f]{16}$")
_V2_KEY_RE = re.compile(r"^v2:[0-9a-f]{32}$")
_VERSIONED_KEY_RE = re.compile(r"^(?P<version>v[^:]+):(?P<digest>[0-9a-f]{32})$")


def legacy_disposition_key(ref: "StaleReference") -> str:
    """Return the preserved version-1 file/surface/matched identity."""

    payload = "\x1f".join((ref.file, ref.retired_surface, ref.matched))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def disposition_key(ref: "StaleReference") -> str:
    """Return the exact version-2 content/context identity for *ref*.

    Each of the five ordered UTF-8 fields is framed as ``byte-length:bytes``.
    The physical line number is intentionally excluded, so harmless movement is
    stable while line or nearest-heading changes create a new identity.
    """

    fields = (
        ref.file,
        ref.retired_surface,
        ref.matched,
        ref.logical_line,
        ref.heading_context,
    )
    payload = b"".join(
        str(len(encoded)).encode("ascii") + b":" + encoded
        for encoded in (field.encode("utf-8") for field in fields)
    )
    return "v2:" + hashlib.sha256(payload).hexdigest()[:32]


def load_dispositions(root: Path | str, *, work=None) -> dict[str, list[str]]:
    """Return ``{key: [statuses...]}``; ``{}`` when absent or unreadable.

    Fail-open by design: an unreadable or malformed store must not suppress
    findings, because silently hiding stale references is the failure this
    channel exists to prevent. The opposite bias (fail-closed) would turn a
    corrupt file into an invisible gap.
    """

    path = Path(root) / DISPOSITIONS_REL
    try:
        if not path.exists():
            return {}
        if work is not None:
            body = work.read(Path(root), path, DISPOSITIONS_REL)
            if body is None:
                return {}
        else:
            body = contained_files.read_contained_bytes(root, path, max_bytes=DEFAULT_SCAN_FILE_BYTES).decode("utf-8")
        data = json.loads(body)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(data, list):
        return {}
    out: dict[str, list[str]] = {}
    for entry in data:
        if work is not None:
            work.candidate()
        if not isinstance(entry, dict):
            continue
        key, status = entry.get("key"), entry.get("status")
        if isinstance(key, str) and isinstance(status, str):
            out.setdefault(key, []).append(status)
    return out


def is_dispositioned(ref: "StaleReference", dispositions: dict[str, list[str]]) -> bool:
    """True for one explicit, syntactically valid v2 historical judgment."""

    key = disposition_key(ref)
    return _V2_KEY_RE.fullmatch(key) is not None and dispositions.get(key) == [HISTORICAL_RECORD]


def disposition_diagnostics(root: Path | str, *, findings=None) -> list[dict[str, object]]:
    """Return read-only store-level states that cannot live in reported findings.

    The three finding channels remain unchanged. This separate projection makes
    settled v2 judgments and dormant legacy entries inspectable without
    re-reporting a suppressed stale reference or inventing a synthetic one.
    """

    dispositions = load_dispositions(root)
    raw_findings = scan_repo(root) if findings is None else findings
    v2_groups: dict[str, list[StaleReference]] = {}
    v1_groups: dict[str, list[StaleReference]] = {}
    for ref in raw_findings:
        v2_groups.setdefault(disposition_key(ref), []).append(ref)
        v1_groups.setdefault(legacy_disposition_key(ref), []).append(ref)

    diagnostics: list[dict[str, object]] = []
    for key, statuses in sorted(dispositions.items()):
        candidates: list[StaleReference]
        if _V1_KEY_RE.fullmatch(key):
            candidates = v1_groups.get(key, [])
            state = (
                "legacy-dormant"
                if not candidates
                else (
                    "legacy-reclassification-required"
                    if len(candidates) == 1
                    else "legacy-ambiguous"
                )
            )
            version = "v1"
        elif _V2_KEY_RE.fullmatch(key):
            candidates = v2_groups.get(key, [])
            if len(candidates) > 1 or len(statuses) > 1:
                state = "v2-ambiguous"
            elif candidates and statuses == [HISTORICAL_RECORD]:
                state = "v2-historical-record"
            else:
                continue
            version = "v2"
        else:
            match = _VERSIONED_KEY_RE.fullmatch(key)
            if match is None or match.group("version") == "v2":
                continue
            candidates = v2_groups.get(f"v2:{match.group('digest')}", [])
            state = "unknown-version"
            version = match.group("version")

        proposed = sorted({disposition_key(ref) for ref in candidates})
        diagnostics.append(
            {
                "disposition_key": key,
                "disposition_key_version": version,
                "disposition_state": state,
                "statuses": list(statuses),
                "candidate_count": len(candidates),
                "candidate_locations": [f"{ref.file}:{ref.line}" for ref in candidates],
                "proposed_v2_keys": proposed,
            }
        )
    return diagnostics


def scan_repo_channels(
    root: Path | str,
) -> tuple[list[StaleReference], list[StaleReference], list[StaleReference]]:
    """Compatible three-channel shape; partial/error work raises with its result."""
    result = scan_repo_result(root)
    if result.state != "complete":
        raise ScanIncomplete(result)
    return result.reconciliation, result.host_permission_flags, result.renderer_provenance_flags


def _partition_findings(raw_findings, dispositions, *, work=None):
    reconciliation = []
    host_permission_flags = []
    renderer_provenance_flags = []
    v2_groups: dict[str, list[StaleReference]] = {}
    v1_groups: dict[str, list[StaleReference]] = {}
    unknown_digests = set()
    for key in dispositions:
        if work is not None:
            work.checkpoint("dispositions")
        match = _VERSIONED_KEY_RE.fullmatch(key)
        if match is not None and match.group("version") != "v2":
            unknown_digests.add(match.group("digest"))
    for ref in raw_findings:
        if work is not None:
            work.checkpoint("dispositions")
        v2_groups.setdefault(disposition_key(ref), []).append(ref)
        v1_groups.setdefault(legacy_disposition_key(ref), []).append(ref)

    for ref in raw_findings:
        if work is not None:
            work.checkpoint("dispositions")
        v2_key = disposition_key(ref)
        v1_key = legacy_disposition_key(ref)
        v2_entries = dispositions.get(v2_key, [])
        v2_digest = v2_key.removeprefix("v2:")
        has_matching_unknown_version = v2_digest in unknown_digests
        duplicate_v2 = len(v2_groups[v2_key]) > 1 or len(v2_entries) > 1
        if duplicate_v2:
            ref = replace(ref, disposition_state="v2-ambiguous")
        elif is_dispositioned(ref, dispositions):
            continue
        elif has_matching_unknown_version:
            ref = replace(ref, disposition_state="unknown-version")
        elif _V1_KEY_RE.fullmatch(v1_key) and HISTORICAL_RECORD in dispositions.get(v1_key, []):
            legacy_candidates = v1_groups[v1_key]
            ref = replace(
                ref,
                disposition_state=(
                    "legacy-reclassification-required"
                    if len(legacy_candidates) == 1
                    else "legacy-ambiguous"
                ),
            )
        if ref.renderer_provenance:
            renderer_provenance_flags.append(ref)
        elif ref.host_permission:
            host_permission_flags.append(ref)
        else:
            reconciliation.append(ref)
    return reconciliation, host_permission_flags, renderer_provenance_flags

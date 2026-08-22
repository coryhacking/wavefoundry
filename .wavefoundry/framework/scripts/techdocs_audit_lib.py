#!/usr/bin/env python3
"""TechDocs publication audit (wave 1vqqi / change 1vmt2).

Computes what the **Refresh TechDocs** workflow's rules imply but nothing else
computes: which pages the built site actually publishes (the ``mkdocs.yml``
``nav`` plus the survivors of ``exclude_docs``), which relative links on those
pages dangle or escape that boundary, whether every ``nav`` target exists,
whether published pages carry their metadata, what the Backstage/TechDocs trio's
marker-derived ownership state is, and whether the agent startup-order documents
kept their heading order.

This module READS. It never writes, and it never NAMES a path outside the
repository root: ``docs_dir`` is resolved through the shared containment helper,
``nav`` entries are screened lexically and then by realpath before ``is_file``,
and every enumerated candidate is re-checked by realpath before it is stat-ed.

It gates nothing. Findings are data; the caller decides what they mean.

Dependencies (mirrored by the ``layering-rules.md`` Boundary Invariants row):
the standard library, ``subprocess_util`` (the bounded worker),
``wave_lint_lib`` (metadata and link primitives),
``render_agent_surfaces`` (trio state and containment), and
``index_state_store`` for every git read. It never imports ``server_impl``,
which imports it. The import chain transitively activates the tool venv through
``lifecycle_id``, so this module is stdlib-only in its own code but does not run
in a bare-stdlib process.
"""
from __future__ import annotations

import json
import os
import re
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True

# Severity words are literals, not an import: `review_evidence.SEVERITY_ORDER`
# also contains `none` and `critical`, which this tool never emits, and
# `blocking` is that module's derived gate boolean rather than a severity rank.
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"

MKDOCS_FILENAME = "mkdocs.yml"
DEFAULT_DOCS_DIR = "docs"

# MkDocs prepends these to every `exclude_docs` block before matching.
MKDOCS_DEFAULT_EXCLUDES = (".*", "/templates/")

# The canonical agent startup-order documents the workflow's audience invariant
# protects, keyed by repository-relative path regardless of `docs_dir`.
STARTUP_ORDER_DOCS = (
    "docs/references/project-overview.md",
    "docs/ARCHITECTURE.md",
)

# Canonical finding order (NOT alphabetical): the sequence below is the order
# `findings` is sorted by, then path, then href.
FINDING_ORDER = (
    "techdocs_trio_partial",
    "techdocs_nav_target_missing",
    "techdocs_nav_target_excluded",
    "techdocs_link_outside_boundary",
    "techdocs_link_missing",
    "techdocs_metadata_incomplete",
    "techdocs_audience_heading_lost",
    "techdocs_index_generated",
)

VERDICT_CLEAN = "clean"
VERDICT_FINDINGS = "findings"
VERDICT_NOT_APPLICABLE = "not_applicable"
VERDICT_DEGRADED = "degraded"

# Degrade reason tokens. Each is a literal constant so the MCP layer can emit it
# from its own call site with a constant code, which the sanctioned-advisory-site
# gate requires (it resolves codes by AST and only when they are literals).
DEGRADE_MKDOCS_ABSENT = "mkdocs_absent"
DEGRADE_MKDOCS_SHAPE = "mkdocs_shape"
DEGRADE_EXCLUDE_DOCS_ABSENT = "exclude_docs_absent"
DEGRADE_DRAFT_DOCS_PRESENT = "draft_docs_present"
DEGRADE_DOCS_DIR_ESCAPES_ROOT = "docs_dir_escapes_root"
DEGRADE_NAV_TARGET_ESCAPES_ROOT = "nav_target_escapes_root"
DEGRADE_SURVIVOR_TARGET_ESCAPES_ROOT = "survivor_target_escapes_root"
DEGRADE_AUDIT_TIMEOUT = "audit_timeout"
DEGRADE_AUDIENCE_NOT_INFORMATIVE = "audience_not_informative"
DEGRADE_GIT_UNAVAILABLE = "git_unavailable"
DEGRADE_BASELINE_UNTRACKED = "baseline_untracked"
DEGRADE_BASELINE_MISSING = "baseline_missing"
DEGRADE_WORKING_TREE_MISSING = "working_tree_missing"
DEGRADE_COMPARE_TO_REFUSED = "compare_to_refused"

# Pattern translation outcomes; see `_translate_pattern`.
# The block-scalar headers this module models: LITERAL scalars only, where one
# line is one pattern. Folded headers (`>`, `>-`, `>+`) join their lines with
# spaces, and an indentation indicator (`|2`) shifts where the content starts;
# neither is modelled, so both degrade rather than being approximated.
_LITERAL_BLOCK_HEADERS = ("|", "|-", "|+")

_PATTERN_OK = "ok"
_PATTERN_INERT = "inert"
_PATTERN_REFUSED = "refused"

# Backtracking budget. The translated regex is exponential in this count, so the
# ceiling must come from an ADVERSARIAL measurement, not from a sample of
# plausible patterns. That distinction has bitten twice: a ceiling of 12 was set
# from a mid-curve figure and admitted a 24s pattern, and the replacement was
# recorded as "about 19ms worst admitted" from a hand sample that a later search
# beat by 23x.
#
# Historical pre-AC-5 search over `?*`/`*?`/`*a` shapes against a
# 60-character page name:
#     2 groups  0.11ms | 3  0.26ms | 4  3.4ms | 5  42ms | 6  448ms
# `excluded()` runs once per survivor page, per nav target and per link. This
# ceiling still matters because the public runner's ten-second process timeout
# bounds a whole audit, not each match. This repository's own block peaks at 1
# group, so 3 keeps 3x headroom over real usage while rejecting the known
# high-growth translation shapes before they consume that aggregate budget.
_MAX_VARIABLE_GROUPS = 3

# The ceiling above bounds the GROUP COUNT. Cost is also cubic in SUBJECT
# length, and the subject is not filesystem-bounded on every call path.
# Historical pre-AC-5 diagnostic measurements (not retained artifact rows):
# `_page_findings` derives it from a markdown link href, so one published page
# carrying a 2500-character href against one admitted pattern took 13.9s end to
# end through the CLI. Measured on the then-slowest observed admitted case:
#     60 chars 0.23ms | 255  15.8ms | 600  198ms | 1000  900ms
# A subject longer than these limits cannot name a file on any supported
# filesystem (255 bytes per component on ext4/APFS/NTFS; 4096 is Linux
# PATH_MAX), so it can never be a published page and its boundary answer is
# never consumed: every caller reaching this with an unbounded subject has an
# existence check that reports the missing target instead.
#
# These are REPRESENTABILITY bounds only. The cost is bounded separately, by the
# ancestor equivalence in `excluded()`, and the distinction is load-bearing: a
# 32-component COST cap was tried here first and was a silent fail-open, because
# a 33-deep tree is legal everywhere, so refusing it made `excluded()` answer
# "published" for an ordinary file under a comment claiming the subject could
# not name one. A cap only belongs here when the subject genuinely cannot exist.
#
# NO BOUND IS CLAIMED HERE, and that is deliberate. Four successive attempts to
# state a worst-admitted per-call cost were each falsified within hours, every
# time because the figure was read off one point of a curve and generalized:
# "19ms" (beaten 23x), "quarter of a millisecond" (held only at a 60-character
# subject), "15.8ms at the component cap" (held only for a single-component
# subject; the true figure was 28.3 SECONDS), and "66ms" (held only for
# segment-local patterns).
#
# The last one is the instructive one. The ancestor equivalence below bounds
# cost only for patterns that cannot match a separator. A CROSSING pattern still
# walks every ancestor, and the group ceiling does not bound that shape. Before
# wave 1vry5, `**/**/*aX` rendered two adjacent ambiguous `(?:.*/)?` prefixes;
# the delivered translator now emits one while still charging both SOURCE
# groups. That removes the redundant case without establishing a general cost
# ceiling: the literal-separated `**/a/**/*aX` remains admitted and is the
# surviving deep-subject timeout reproduction.
#
# So the honest statement is that matcher cost is not bounded by these local
# ceilings. The public runner supplies the hard aggregate bound by terminating
# its isolated worker after ten seconds; the local collapse is only a semantic
# deduplication (`**/**/` and `**/` denote the same language).
_MAX_COMPONENT_CHARS = 255
_MAX_SUBJECT_CHARS = 4096
TECHDOCS_AUDIT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    path: str
    detail: str
    href: str = ""

    def as_dict(self) -> dict:
        out = {"code": self.code, "severity": self.severity, "path": self.path, "detail": self.detail}
        if self.href:
            out["href"] = self.href
        return out


@dataclass(frozen=True)
class TechdocsAuditReport:
    repo_root: str
    trio: dict
    publication: dict
    findings: tuple
    audience: dict
    summary: dict
    degraded: tuple

    def as_dict(self) -> dict:
        return {
            "repo_root": self.repo_root,
            "trio": self.trio,
            "publication": self.publication,
            "findings": [f.as_dict() for f in self.findings],
            "audience": self.audience,
            "summary": self.summary,
            "degraded": list(self.degraded),
        }


def _report_from_dict(data: dict) -> TechdocsAuditReport:
    """Rehydrate the private worker's JSON envelope."""
    return TechdocsAuditReport(
        repo_root=str(data["repo_root"]),
        trio=dict(data["trio"]),
        publication=dict(data["publication"]),
        findings=tuple(Finding(
            code=str(item["code"]),
            severity=str(item["severity"]),
            path=str(item["path"]),
            detail=str(item["detail"]),
            href=str(item.get("href", "")),
        ) for item in data["findings"]),
        audience=dict(data["audience"]),
        summary=dict(data["summary"]),
        degraded=tuple(str(item) for item in data["degraded"]),
    )


# ---------------------------------------------------------------------------
# mkdocs.yml: recognized-shape parsing, never a third-party YAML dependency.
# ---------------------------------------------------------------------------

def _nav_scalar(value: str) -> "str | None":
    """Return one modeled nav-path scalar, or ``None`` when YAML rules are needed."""
    value = value.strip()
    if not value:
        return None
    if value[0] in ("'", '"'):
        quote = value[0]
        if len(value) < 3 or value[-1] != quote:
            return None
        payload = value[1:-1]
        # Exactly one wrapper is modeled. YAML quote escaping and double-quoted
        # backslash escapes deliberately remain outside this dependency-free parser.
        if not payload or quote in payload or (quote == '"' and "\\" in payload):
            return None
        return payload
    if value[-1:] in ("'", '"'):
        return None
    # These leading indicators introduce YAML nodes rather than plain scalars:
    # flow collections, anchors/aliases/tags, block scalars, directives, and
    # reserved syntax. They are intentionally outside this recognized-shape
    # parser and must degrade instead of becoming filenames.
    if value[0] in ",[]{}#&*!|>%@`":
        return None
    if value[0] in "-?:" and (len(value) == 1 or value[1].isspace()):
        return None
    # In a plain YAML scalar, separation whitespace makes ``#`` a comment. Keeping
    # only the prefix would guess at operator intent, so the whole shape degrades.
    # A whole-value comment reaches this helper as ``#...`` after the mapping's
    # structural whitespace has already been removed, so it needs its own arm.
    if re.search(r"\s#|:(?:\s|$)", value):
        return None
    return value


def _nav_entry(line: str) -> "tuple[str, str | None, int]":
    """Classify one nav line as ``leaf``, ``section``, or ``unsupported``."""
    indent_text = line[:len(line) - len(line.lstrip())]
    indent = len(indent_text)
    if "\t" in indent_text:
        return "unsupported", None, indent
    item = line.lstrip()
    if not item.startswith("-") or len(item) == 1 or not item[1].isspace():
        return "unsupported", None, indent
    item = item[2:].lstrip()
    if not item:
        return "unsupported", None, indent

    title, separator, tail = item.partition(":")
    if separator:
        if not title.strip():
            return "unsupported", None, indent
        if not tail.strip():
            return "section", None, indent
        value = tail
    else:
        value = item
    path = _nav_scalar(value)
    if path is None:
        return "unsupported", None, indent
    return "leaf", path, indent


def _in_sub_block(line: str) -> bool:
    """True while *line* still belongs to the block under a mapping key.

    Indentation alone is not the test. A block sequence under a mapping key is
    canonical YAML at zero indent (``nav:`` followed by ``- Home: index.md`` in
    column 0) and is what PyYAML and js-yaml emit by default, so a collector
    that stops at the first unindented line reads such a file as empty. The
    block ends at the next top-level mapping key, not at the next unindented
    line.
    """
    if not line.strip():
        return True
    if line[:1].isspace():
        return True
    # A comment at column 0 sits INSIDE the block as far as YAML is concerned.
    # Treating it as a terminator truncated the read and still reported `clean`:
    # an `exclude_docs` block whose first line is a comment parsed as an empty
    # boundary, which publishes every agent surface. The shipped mkdocs template
    # opens with a column-0 comment and invites the operator to edit freely, so
    # this is the ordinary case rather than a hostile one.
    if line.lstrip().startswith("#"):
        return True
    return line.lstrip().startswith("-")


def _unterminated_quote(rest: str) -> bool:
    """True when *rest* opens a quoted scalar it does not close on this line.

    A multi-line quoted scalar carries YAML folding and escape rules that this
    recognized-shape parser deliberately does not implement, so it degrades as
    `mkdocs_shape` rather than silently keeping only the first line.
    """
    if rest[:1] not in ("'", '"'):
        return False
    quote = rest[0]
    if quote == "'":
        # YAML escapes a single quote by doubling it.  A line ending in ``''``
        # therefore has not necessarily closed the scalar: in ``'foo''`` the
        # final pair is one literal quote and the scalar continues on the next
        # line.  Treating the second quote as the closer truncated a valid YAML
        # value while leaving ``shape_ok`` true.
        i = 1
        while i < len(rest):
            if rest[i] != "'":
                i += 1
                continue
            if i + 1 < len(rest) and rest[i + 1] == "'":
                i += 2
                continue
            return False
        return True
    return not (len(rest) > 1 and rest.endswith(quote))


def parse_mkdocs(text: str) -> dict:
    """Parse the recognized shape. Returns docs_dir, nav, exclude_docs, shape_ok.

    `exclude_docs` is ``None`` when the key is absent entirely, which is NOT the
    same as an empty block: `techdocs-cli generate` re-serializes the file in its
    own supported-key order and drops keys outside that allowlist, so a missing
    block must degrade rather than yield a boundary that publishes everything.
    """
    docs_dir = DEFAULT_DOCS_DIR
    draft_docs_present = False
    nav: list[str] = []
    exclude: list[str] | None = None
    shape_ok = True

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if not line[:1].isspace():
            key, _, rest = stripped.partition(":")
            # A serializer may quote keys ("nav":). Comparing the raw token made
            # every key silently unrecognized, so nav parsed empty and docs_dir
            # fell back to its default with shape_ok still true.
            key = key.strip().strip("'\"")
            rest = rest.strip()
            if key == "docs_dir":
                docs_dir = rest.strip("'\"") or DEFAULT_DOCS_DIR
                i += 1
                continue
            if key == "nav":
                # YAML is last-wins on a repeated key; appending concatenated
                # the two blocks and invented a missing-target finding.
                nav = []
                if rest:
                    shape_ok = False
                    i += 1
                    continue
                i += 1
                base_indent: int | None = None
                active_section = False
                child_indent: int | None = None
                while i < len(lines) and _in_sub_block(lines[i]):
                    entry = lines[i]
                    i += 1
                    if not entry.strip() or entry.strip().startswith("#"):
                        # Comments are skipped, not treated as a malformed shape;
                        # the exclude_docs collectors already do the same.
                        continue
                    kind, path, indent = _nav_entry(entry)
                    if kind == "unsupported":
                        shape_ok = False
                        active_section = False
                        continue
                    if base_indent is None:
                        base_indent = indent
                    if indent < base_indent:
                        shape_ok = False
                        active_section = False
                        continue
                    if indent == base_indent:
                        active_section = kind == "section"
                        child_indent = None
                        if kind == "leaf":
                            nav.append(path or "")
                        continue
                    # One nested sequence beneath a root section is modeled. A
                    # nested section would admit a second section depth, while a
                    # leaf without an active root section is malformed/ambiguous.
                    if not active_section or kind != "leaf":
                        shape_ok = False
                        active_section = False
                        continue
                    if child_indent is None:
                        child_indent = indent
                    elif indent != child_indent:
                        shape_ok = False
                        continue
                    nav.append(path or "")
                continue
            if key == "draft_docs":
                # A documented MkDocs key that removes pages from a BUILD
                # (`InclusionLevel.DRAFT`). This module does not model it, and
                # not reading it at all meant a page MkDocs omits was reported
                # as published with a clean verdict. Noticing it and degrading
                # is the honest floor.
                draft_docs_present = True
                i += 1
                while i < len(lines) and _in_sub_block(lines[i]):
                    i += 1
                continue
            if key == "exclude_docs":
                if rest[:1] in ("|", ">") and rest not in _LITERAL_BLOCK_HEADERS:
                    # A block-scalar header this module does not model. The
                    # enumeration used to be a five-member allowlist with an
                    # approximating fall-through, and BOTH halves were wrong.
                    #
                    # Fall-through: an indentation indicator (`|2`, `|-2`,
                    # `|2-`, `>+2`) missed the allowlist, reached the
                    # single-line-scalar branch below, and became a
                    # one-element pattern list holding the HEADER TOKEN, with
                    # shape_ok true and no degrade. The operator's whole
                    # exclusion block was discarded silently and a private
                    # tree was reported as published. `|2` is not a hostile
                    # shape: PyYAML emits exactly it when the block's first
                    # content line carries leading whitespace.
                    #
                    # Allowlist: `>` and `>-` were IN it and were read
                    # line-per-pattern, but YAML FOLDS them into one
                    # space-joined scalar, so a two-line block became one
                    # pattern that matches nothing. That produced false
                    # findings, including one at the top severity rank,
                    # against a tree `mkdocs build --strict` accepts.
                    #
                    # Folded semantics are exactly what this module declined
                    # to implement for multi-line quoted scalars, so the rule
                    # is the same here: recognize what is modelled, degrade on
                    # everything else, and never approximate.
                    shape_ok = False
                    i += 1
                    while i < len(lines) and _in_sub_block(lines[i]):
                        i += 1
                    continue
                if rest in _LITERAL_BLOCK_HEADERS:
                    i += 1
                    collected: list[str] = []
                    base_indent = None
                    while i < len(lines) and _in_sub_block(lines[i]):
                        raw = lines[i]
                        value = raw.strip()
                        i += 1
                        if value and not value.startswith("#"):
                            indent = len(raw) - len(raw.lstrip())
                            if base_indent is None:
                                base_indent = indent
                            elif indent != base_indent:
                                # In a YAML block scalar the FIRST content line
                                # fixes the block's indentation and anything
                                # deeper is literal leading whitespace in the
                                # value. gitignore treats leading whitespace as
                                # significant (only TRAILING whitespace is
                                # stripped), so `  /prompts/*` followed by
                                # `   x.md` really carries the pattern ` x.md`.
                                # Stripping it diverged from a loadable config
                                # in BOTH directions: measured, this module
                                # published ` x.md` where MkDocs hides it, and
                                # hid `x.md` where MkDocs publishes it. Leading
                                # whitespace is not modelled, so the shape
                                # degrades rather than being guessed at.
                                #
                                # The test is `!=` rather than `>` so the rule
                                # is symmetric: a LESS indented continuation
                                # ends the scalar and makes the whole document
                                # a YAML parse error, so MkDocs cannot build
                                # the site at all. Reading a boundary out of a
                                # file that does not load is the same silent
                                # approximation from the other side.
                                shape_ok = False
                            collected.append(value)
                    exclude = collected
                    continue
                if rest.startswith("["):
                    # A YAML flow sequence is outside the recognized shape.
                    shape_ok = False
                    i += 1
                    continue
                if _unterminated_quote(rest):
                    # A quoted scalar spanning lines: degrade rather than keep
                    # only its first line as if it were the whole block.
                    shape_ok = False
                    i += 1
                    while i < len(lines) and _in_sub_block(lines[i]):
                        i += 1
                    continue
                if rest:
                    exclude = [rest.strip("'\"")]
                    i += 1
                    continue
                # A block sequence under the key.
                i += 1
                collected = []
                while i < len(lines) and _in_sub_block(lines[i]):
                    value = lines[i].strip()
                    i += 1
                    if value.startswith("- "):
                        item = value[2:].strip()
                        # An inline comment ends a sequence entry. In the block
                        # scalar form above `#` is literal, so this strip is
                        # deliberately NOT applied there.
                        if "#" in item:
                            head = item.split("#", 1)[0]
                            if head != item and (head == "" or head[-1].isspace()):
                                item = head.strip()
                        collected.append(item.strip("'\""))
                    elif value and not value.startswith("#"):
                        shape_ok = False
                exclude = collected
                continue
        i += 1
    return {"docs_dir": docs_dir, "nav": nav, "exclude_docs": exclude,
            "shape_ok": shape_ok, "draft_docs_present": draft_docs_present}


def _class_end(pattern: str, start: int) -> "int | None":
    """Index of the `]` closing the character class opened at *start*.

    A `!` or `^` may lead, and a `]` in first position is a literal member, so
    neither terminates the class. Returns None when the class is unterminated.
    """
    j = start + 1
    if j < len(pattern) and pattern[j] in "!^":
        j += 1
    if j < len(pattern) and pattern[j] == "]":
        j += 1
    # The class ends at the first `]`, escaped or not: pathspec (the matcher
    # MkDocs uses) does not honour backslash escapes inside a class, so `[a\]b]`
    # is the class `a\` followed by the literal `b]`. Measured, not assumed.
    #
    # A `/` also ends the search, because pathspec splits the pattern into
    # SEGMENTS before it handles classes, so a class can never span a
    # separator. Scanning past `/` folded `[abc/[a-z]` into one Python class
    # holding `/`, which matched almost any name where pathspec matched
    # nothing: measured against a real `mkdocs build`, the non-negated form
    # over-excluded and the negated form published a site that really is empty,
    # with `degraded: []` either way.
    while j < len(pattern) and pattern[j] not in "]/":
        j += 1
    # Stopping on `/` means the class never closed inside its own segment, which
    # is the unterminated case, not a class ending at that index.
    return j if j < len(pattern) and pattern[j] == "]" else None


def _translate_pattern(pattern: str) -> tuple:
    """Translate one gitignore-style pattern. Returns (status, negated, regex).

    `status` is one of three, and the distinction is measured against pathspec
    (the matcher MkDocs actually uses) rather than assumed:

    * `ok` — translated; `regex` matches what pathspec matches.
    * `inert` — pathspec ACCEPTS the pattern and it matches nothing (an
      unterminated class is the common case). `regex` is None. This must NOT
      degrade: the config loads and the computed boundary is correct.
    * `refused` — pathspec cannot compile it, so MkDocs cannot load the config
      at all, or this module cannot translate it safely. `regex` is None and
      `unsupported_patterns` reports it so the run degrades instead of
      presenting a boundary for a site that cannot be built.

    MkDocs semantics are gitignore's: last match wins, `!` re-includes, a
    leading `/` anchors at `docs_dir`, a slash anywhere else also anchors, `*`
    does not cross `/`, `**` does, and a trailing `/` names a directory and
    everything under it.
    """
    # Leading whitespace is significant to gitignore/pathspec.  It can arrive
    # through a quoted inline scalar or quoted sequence member even though the
    # recognized block-scalar parser rejects uneven indentation.  Stripping it
    # reversed the publication boundary in both directions, so refuse the
    # unmodelled carrier before normalizing insignificant surrounding space.
    if pattern[:1].isspace() and pattern.strip():
        return _PATTERN_REFUSED, False, pattern.rstrip().endswith("/"), None, False
    pattern = pattern.strip()
    if not pattern or pattern.startswith("#"):
        return _PATTERN_INERT, False, False, None, False
    negated = pattern.startswith("!")
    if negated:
        pattern = pattern[1:]
    if not pattern:
        # A bare `!` is refused by pathspec, not merely inert.
        return _PATTERN_REFUSED, negated, False, None, False
    if "//" in pattern:
        # `**//`, `/*//`, `a//b`. `rstrip("/")` collapsed the run and left a
        # live matcher a segment too wide: measured, both oracles say these
        # match NOTHING, while this module excluded every subtree page under
        # them. Translating them faithfully means reproducing pathspec's own
        # normalization, which this module does not attempt, so they are
        # refused and the run degrades instead of presenting a wrong boundary.
        return _PATTERN_REFUSED, negated, pattern.endswith("/"), None, False
    dir_only = pattern.endswith("/")
    pattern = pattern.rstrip("/")
    if not pattern:
        # A bare `/`. This was recorded as INERT on a pathspec-only
        # measurement, which was the wrong LAYER for the claim: `/` on its own
        # does match nothing, but `!/` is a live RE-INCLUDE, and `/*` + `!/`
        # publishes every subtree page at both the pathspec and the
        # `get_files` layer while this module excluded all of them. Refused
        # rather than guessed at.
        return _PATTERN_REFUSED, negated, dir_only, None, False
    # Anchoring is decided BEFORE the `/**` strip below. Deciding it after let
    # the strip remove a pattern's only slash, so `sub/**/` became the FLOATING
    # `^(?:.*/)?sub$` and stopped excluding its own subtree: measured against a
    # real `mkdocs build`, two published pages went unchecked and any nav entry
    # into them produced a false `techdocs_nav_target_excluded` at the top
    # severity rank. `/internal/**/` and `**/internal/**/` were unaffected,
    # which is why the root-anchored form the shipped test used could not see
    # it: only `NAME/**/`, whose sole slash is the one the strip removes.
    anchored = pattern.startswith("/") or "/" in pattern
    while dir_only and pattern.endswith("/**") and pattern != "/**":
        # `dir/**/` : keeping both the trailing `**` and the dir_only flag left
        # the body as `dir/.*`, which disabled the DIRECT tier (dir_only never
        # matches a file) while never matching the ancestor NAME `dir` either.
        # Both tiers missed and the exclusion was silently a no-op.
        #
        # It stays an ANCESTOR-tier pattern rather than becoming a direct one:
        # measured against `mkdocs.structure.files.get_files`, `dir/**/` alone
        # excludes the subtree, but `dir/**/` + `!/dir/` PUBLISHES it, which is
        # only expressible if the exclusion is a directory match a directory
        # negation can cancel. Dropping dir_only instead made 20 blocks
        # fail-closed. So drop the redundant `/**` and keep the flag.
        #
        # The `pattern != "/**"` guard is what keeps `/**/` out of here. Without
        # it the strip left an EMPTY body, `anchored` computed False on the
        # empty string, and the pattern compiled to a matcher for nothing at
        # all: measured against a real `mkdocs build`, `/**/` published seven
        # pages the built site does not contain, including an agent surface and
        # an unpublished tree, with no degrade. (Unpublished, not private:
        # `exclude_docs` is a PUBLICATION boundary, not access control. Every
        # one of those files stays readable to anyone with repository access,
        # on GitHub or anywhere else; what the boundary decides is whether the
        # built site serves it.) It is the only fail-OPEN shape found
        # in 1998 oracle-compared blocks. Kept whole, `/**/` reaches the loop as
        # bare `**` and becomes the ancestor-tier `.*` that both oracles agree
        # on: every subtree page excluded, root-level pages untouched.
        #
        # It is a `while`, not an `if`, because one strip can leave another
        # `/**` behind: `/internal/**/**/` compiled to `^internal/.*$` with
        # dir_only set, which the direct tier skips and no ancestor matches, so
        # both tiers missed and the subtree published. Found by a 7200-block
        # randomized differential against a real `get_files`, as the last
        # fail-open in that corpus.
        pattern = pattern[: -len("/**")]
    pattern = pattern.lstrip("/")

    out: list[str] = []
    variable_groups = 0
    # Whether the compiled regex can match a subject CONTAINING a separator.
    # Only `**` forms, a literal `/`, and the floating prefix can; `*`, `?`,
    # classes and literals are all segment-local. `excluded()` uses this to skip
    # the ancestor walk for a pattern that provably cannot match any ancestor
    # past the first, which is what bounds the cost.
    crosses_separator = not anchored
    i = 0
    n = len(pattern)
    while i < n:
        if pattern.startswith("**/", i):
            # Adjacent floating prefixes denote the same language as one. Keep
            # charging every SOURCE group below while emitting only one copy;
            # admission is intentionally independent from regex deduplication.
            if not out or out[-1] != "(?:.*/)?":
                out.append("(?:.*/)?")
            crosses_separator = True
            variable_groups += 1
            i += 3
        elif pattern.startswith("/**", i) and i + 3 == n:
            out.append("/.*")
            crosses_separator = True
            variable_groups += 1
            i += 3
        elif pattern[i] == "*":
            run_start = i
            while i < n and pattern[i] == "*":
                i += 1
            whole_segment = (
                i - run_start == 2
                and (run_start == 0 or pattern[run_start - 1] == "/")
                and (i == n or pattern[i] == "/")
            )
            if whole_segment:
                # A `**` run CROSSES separators when it is a whole path segment.
                # EXACTLY two stars: pathspec does not read `***` as `**`, and
                # treating any run of two-or-more that way published pages the
                # built site hides.
                # gitignore names three positions -- leading `**/`, trailing
                # `/**`, and `/**/` -- and this module had a branch for each,
                # which is why the fourth went missing: `**` as the ONLY segment.
                # `lstrip("/")` above removes the anchor, so `/**` reaches this
                # loop as bare `**` and used to compile to `[^/]*`, matching only
                # top-level names. In a multi-pattern block that demoted the
                # match to the ancestor tier, where a later directory negation
                # outranks it, and the deny-by-default `/**` + allowlist idiom
                # that seed 178 step 6 leads operators to silently published
                # everything the allowlist re-included.
                out.append(".*")
                crosses_separator = True
            else:
                # Any other run is a regular `*`, which does not cross a
                # separator: gitignore reads `a**b` exactly as `a*b`.
                out.append("[^/]*")
            variable_groups += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        elif pattern[i] == "\\" and i + 1 >= n:
            # A lone trailing backslash: pathspec refuses the pattern, so the
            # config does not load. Escaping it produced a live regex instead,
            # the exact inverse of what the oracle does.
            return _PATTERN_REFUSED, negated, dir_only, None, False
        elif pattern[i] == "\\" and i + 1 < n:
            # A backslash escapes the next character. Without this branch the
            # backslash itself was escaped into the regex, so the pattern could
            # only match a path literally containing one: every escaped pattern
            # silently under-excluded, which publishes a page meant to be hidden.
            if pattern[i + 1] == "/":
                # pathspec refuses a backslash that actually escapes a path
                # separator. A doubled backslash is consumed as a pair before
                # the following slash reaches this branch, preserving accepted
                # forms such as `a\\/b`.
                return _PATTERN_REFUSED, negated, dir_only, None, False
            out.append(re.escape(pattern[i + 1]))
            i += 2
        elif pattern[i] == "[":
            close = _class_end(pattern, i)
            if close is None:
                # An unterminated class matches NOTHING, and pathspec ACCEPTS
                # it (measured: it compiles to an inert matcher). So the config
                # still loads and the boundary is correct without it. Reading it
                # as a literal `[` invented a boundary neither oracle has, and
                # degrading on it wrongly failed a config MkDocs can build.
                return _PATTERN_INERT, negated, dir_only, None, False
            else:
                inner = pattern[i + 1:close]
                if inner.startswith("!"):
                    inner = "^" + inner[1:]
                # A backslash inside the class is a literal member, not an
                # escape (pathspec reads it that way). Doubling it keeps the
                # class valid; leaving it raw made `[a\]` an unterminated set
                # that only re.compile rejected.
                inner = inner.replace("\\", "\\\\")
                rendered = "[" + inner + "]"
                # A class can still match a separator even though `_class_end`
                # forbids a LITERAL `/` inside it: `[!q]` compiles to `[^q]`,
                # and an ASCII range such as `[.-0]` spans `/`. Claiming
                # segment-locality by syntax alone was wrong in exactly this
                # way, and it fails OPEN. Ask the compiled class instead.
                try:
                    with warnings.catch_warnings():
                        # Use the same warning policy as the final compile below.
                        # Without it, an inherited ``-W error`` converted a
                        # conservatively refusable nested set into worker death
                        # before the protected compile was reached.
                        warnings.simplefilter("error")
                        if re.compile(rendered).match("/"):
                            crosses_separator = True
                except Exception:
                    # A class the compiler rejects must still reach the refusal
                    # below rather than being decided here.
                    crosses_separator = True
                out.append(rendered)
                i = close + 1
        else:
            if pattern[i] == "/":
                crosses_separator = True
            out.append(re.escape(pattern[i]))
            i += 1
    prefix = "" if anchored else "(?:.*/)?"
    body = "".join(out)
    if not anchored:
        variable_groups += 1  # the floating `(?:.*/)?` prefix backtracks too
    if variable_groups > _MAX_VARIABLE_GROUPS:
        # Catastrophic backtracking is reachable from a target's own config:
        # `?*` repeated renders as `[^/][^/]*` pairs, which is exponential, and
        # 52 bytes of pattern wedged the tool indefinitely against a 40-char
        # page name. `excluded()` runs once per survivor page, per nav target
        # and per link. The public runner's process timeout is the final
        # aggregate backstop; this refusal keeps known-bad translations from
        # needlessly consuming that budget.
        #
        # Refusing above the ceiling degrades instead of hanging, but note what
        # that does NOT claim: everything at or below the ceiling still costs
        # what the curve above says it costs, and the ceiling is what keeps that
        # bounded. Raising it re-opens the hang without changing a line here.
        return _PATTERN_REFUSED, negated, dir_only, None, False
    # EXACT match, with no subtree tail. The subtree effect is directory
    # PRUNING and belongs in `excluded()`'s ancestor walk, not in this regex.
    # Baking a `(?:/.*)?` tail in here is what made a negated directory pattern
    # re-include files underneath it, which silenced both `nav`-excluded and
    # link-outside-boundary findings on a boundary MkDocs really does enforce.
    try:
        with warnings.catch_warnings():
            # `re` only WARNS about `[[:alpha:]]`-style nested sets under default
            # filters, leaking to stderr and compiling something neither oracle
            # agrees with, and RAISES the same FutureWarning under -W error.
            # Escalating locally makes the outcome independent of how the host
            # was launched.
            warnings.simplefilter("error")
            return (_PATTERN_OK, negated, dir_only,
                    re.compile("^" + prefix + body + "$"), crosses_separator)
    except Exception:
        # Deliberately Exception, not a class list. This is a small pure
        # translation, and ANY failure here means the pattern cannot be
        # translated. Enumerating classes is what failed four times: OSError
        # missed UnicodeDecodeError, then the tuple missed re.error, then it
        # missed bare ValueError, then it missed FutureWarning. Refused, so the
        # caller degrades rather than guessing.
        return _PATTERN_REFUSED, negated, dir_only, None, False


def _pattern_regex(pattern: str) -> "tuple[bool, bool, re.Pattern, bool] | None":
    """(negated, dir_only, exact-match regex, crosses_separator), or None."""
    status, negated, dir_only, regex, crosses = _translate_pattern(pattern)
    if status != _PATTERN_OK:
        return None
    return negated, dir_only, regex, crosses


def unsupported_patterns(patterns: "list[str]") -> "list[str]":
    """Patterns this module will not compute a boundary from, so the caller degrades.

    Two disjoint reasons, and the headline used to name only the first:
    pathspec cannot compile it (so MkDocs cannot load the config at all), OR
    this module cannot translate it safely (a nested-set class that `re` only
    warns about, or a pattern whose translation exceeds the backtracking
    budget). MkDocs CAN load that second group; refusing it is a deliberate
    conservative choice that degrades and over-reports rather than guessing.

    ONLY the `refused` class. An `inert` pattern (an unterminated class, a
    comment, a blank) is accepted by pathspec and matches nothing, so the config
    loads and the computed boundary is correct; degrading on those wrongly
    failed a buildable site. Measured against pathspec 1.1.1 rather than
    assumed: of thirteen patterns this module cannot translate, eight are
    accepted by pathspec and only bad ranges, a bare `!`, and a lone trailing
    backslash are genuinely refused.
    """
    return [p for p in patterns if _translate_pattern(p)[0] == _PATTERN_REFUSED]


def excluded(rel_posix: str, patterns: "list[str]") -> bool:
    """True when MkDocs would remove *rel_posix* (a docs_dir-relative path).

    TWO tiers, not one last-match pass. A pattern matches a path either DIRECTLY
    (its regex matches the full path) or VIA AN ANCESTOR (it matches a parent
    directory, reaching the file through that directory). Direct matches decide
    the answer whenever any exist; ancestor matches decide only when none do.
    Within each tier, last match wins. A `dir/` pattern never matches directly,
    because it names a directory.

    Worked shapes, all measured against the oracle:

    * `/*` + `!/prompts/` publishes `prompts/index.md`. Neither matches
      directly, so the ancestor tier decides and the directory negation wins.
    * `/private/**` + `!/private/notes/` still excludes `private/notes/x.md`.
      `/private/**` matches DIRECTLY, so the directory negation never reaches
      the file. `!/private/notes/x.md` would, being direct itself.
    * `!/references/**` + `/*` publishes `references/x.md` even though the
      exclusion comes last, because `/*` only reaches the file through the
      `references` directory while the negation is direct.

    Two simpler models were implemented and MEASURED WRONG before this one: a
    single last-match pass over file paths with a subtree tail baked into each
    regex (fails open, 83 of 14649 multi-pattern comparisons), and git's own
    ancestor-PRUNING model where an excluded directory cannot be re-entered
    (52 of 18810, because pathspec documents a deliberate deviation from git and
    does allow re-including a file out of an excluded directory).

    Failing open here is the expensive direction: reporting an excluded page as
    published silences `techdocs_nav_target_excluded` (high) and
    `techdocs_link_outside_boundary` on a 404 that `mkdocs build` really emits.
    The oracle is `pathspec.gitignore.GitIgnoreSpec`, which is what MkDocs
    constructs in `config_options.PathSpec.run_validation`.
    """
    parts = rel_posix.split("/")
    if (len(rel_posix) > _MAX_SUBJECT_CHARS
            or any(len(p) > _MAX_COMPONENT_CHARS for p in parts)):
        # Unrepresentable as a file, so MkDocs has nothing to remove and the
        # answer is False by construction rather than by matching. Checked
        # before compiling, because the cost this avoids is in the match.
        return False

    compiled = []
    for raw in list(MKDOCS_DEFAULT_EXCLUDES) + list(patterns):
        entry = _pattern_regex(raw)
        if entry is not None:
            compiled.append(entry)

    ancestors = ["/".join(parts[:depth]) for depth in range(1, len(parts))]

    direct_verdict = None
    ancestor_verdict = None
    for negated, dir_only, regex, crosses in compiled:
        if not dir_only and regex.match(rel_posix):
            direct_verdict = not negated
        else:
            # A regex that cannot match a separator can only ever match the
            # FIRST ancestor, since every deeper ancestor contains one. Skipping
            # the rest is what bounds the cost: the walk re-matches each pattern
            # against every prefix, and every prefix begins with the same
            # leading component, so a segment-local pattern paid that component's
            # cost once per ancestor for no possible gain. Measured, one
            # admitted pattern against a legal 1901-component subject went from
            # 28.3 SECONDS to 0.3ms. This is an exact equivalence, not a
            # heuristic, so no subject is refused for it and no representability
            # claim is needed.
            reachable = ancestors if crosses else ancestors[:1]
            if any(regex.match(a) for a in reachable):
                ancestor_verdict = not negated
    if direct_verdict is not None:
        return direct_verdict
    return bool(ancestor_verdict)


# ---------------------------------------------------------------------------
# Containment, survivor enumeration, links.
# ---------------------------------------------------------------------------


def _contained(repo_root: Path, rel: str) -> "Path | None":
    """Resolve *rel* under the root, or None when it escapes.

    Uses the shared helper (`render_agent_surfaces._contained_review_carrier_path`),
    which raises on escape; its message names a review carrier, so the caller maps
    the refusal to this module's own degrade token instead of echoing it.
    `server_impl.resolve_path_under_root` is deliberately NOT used: it returns a
    server envelope fragment, and `server_impl` imports this module.
    """
    from render_agent_surfaces import _contained_review_carrier_path  # noqa: PLC0415

    try:
        return _contained_review_carrier_path(repo_root, rel)
    except RuntimeError:
        return None


def survivor_pages(
    repo_root: Path,
    docs_root: Path,
    patterns: "list[str]",
    unsafe_targets: "list[str] | None" = None,
) -> "list[str]":
    """Every published markdown page, as docs_dir-relative posix paths.

    Walks the way MkDocs walks: `mkdocs.structure.files.get_files` uses
    `os.walk(..., followlinks=True)` and prunes no directories, so both
    symlinked FILES and symlinked DIRECTORIES that stay inside the root are
    followed here too. An earlier version used `rglob`, which never descends a
    symlinked directory on any supported version, and an earlier repair fixed
    only the file half while citing `followlinks` (which governs the directory
    half) as its reason. Both left pages the audit never saw, and a page the
    audit never sees is a page whose links and metadata are never checked --
    the expensive direction.

    Two guards, both load-bearing:

    * **Containment.** A directory or file whose realpath leaves the repository
      root is refused and never descended. This is a KNOWN, deliberate
      divergence: MkDocs publishes that content and this module will not read
      outside the root, so the audit reports fewer pages than the built site
      contains. Refusing is the safe direction and the containment claim depends
      on it, but the disagreement is real and recorded rather than hidden.
    * **Cycle detection.** `followlinks=True` lets a symlink cycle re-enter
      directories repeatedly and `os.walk` does not guard it. It is not strictly
      infinite (the OS symlink limit ends it, at a platform-dependent depth), but
      it is unbounded in any useful sense: a two-node mutual alias enumerated 33
      paths for 3 real files. The guard tests membership in the
      CHAIN of directories currently being walked, which is exactly "descending
      this would re-enter a directory I am already inside". Two narrower guards
      were tried and are wrong: self-ancestry alone misses a mutual alias
      (`docs/a/link -> ../b` with `docs/b/link -> ../a` enumerated 33 paths for
      3 real files, terminating only on the OS symlink limit), and a global
      "realpath already seen" set terminates but also drops a legitimate alias
      to an already-walked directory, trading a hang for under-enumeration.

      KNOWN DIVERGENCE on a cyclic tree, deliberate and bounded: MkDocs has NO
      cycle guard, so its own walk yields a platform-dependent result (33 paths
      here, at the macOS limit of 32 symlink levels; 40 on Linux). This module
      returns a bounded, deterministic subset instead. A cyclic docs tree has no
      well-defined published set, so matching MkDocs exactly is not available;
      terminating is.

    Exclusion is decided only by `excluded()`. Dotfiles are removed by the
    MkDocs default `.*` rather than by a separate short-circuit here, so a block
    that re-includes one with `!` gets the same answer from this walk and from
    `excluded()`. When supplied, `unsafe_targets` receives docs-relative logical
    paths for refused escaping files and directories; callers use that channel
    to make the incomplete boundary explicit without exposing external paths.
    """
    resolved_root = os.path.realpath(str(repo_root))

    def _inside(real: str) -> bool:
        return real == resolved_root or real.startswith(resolved_root + os.sep)

    survivors: list[str] = []
    refused_targets = unsafe_targets if unsafe_targets is not None else []
    # Cycle detection over the CHAIN of directories actually walked, not over a
    # global set of realpaths. Both weaker guards were tried and are wrong:
    #   * self-ancestry only (a child resolving to an ancestor of its immediate
    #     parent) misses mutual aliases -- `docs/a/link -> ../b` with
    #     `docs/b/link -> ../a` enumerated 33 survivors for 3 real files, and a
    #     three-node branching alias 49, terminating only because the OS returns
    #     ELOOP at a platform-dependent depth (32 on macOS, 40 on Linux).
    #   * a global "realpath already seen" set terminates but also drops a
    #     legitimate alias to an already-walked directory, which MkDocs
    #     publishes, so it trades a hang for under-enumeration.
    # Membership in the chain is exactly "descending this would re-enter a
    # directory I am already inside", which terminates and leaves siblings alone.
    chains: dict = {str(docs_root): frozenset({os.path.realpath(str(docs_root))})}
    for dirpath, dirnames, filenames in os.walk(str(docs_root), followlinks=True):
        chain = chains.pop(dirpath, None)
        if chain is None:  # pragma: no cover - os.walk always yields top-down
            chain = frozenset({os.path.realpath(dirpath)})
        kept = []
        for name in dirnames:
            child = os.path.join(dirpath, name)
            child_real = os.path.realpath(child)
            # Refuse to leave the root, and never stat past it: the one
            # deliberate divergence from MkDocs, which publishes that content.
            if not _inside(child_real):
                logical = (Path(dirpath) / name).relative_to(docs_root).as_posix()
                refused_targets.append(logical + "/")
                continue
            if child_real in chain:
                continue
            kept.append(name)
            chains[child] = chain | {child_real}
        dirnames[:] = kept
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            full = Path(dirpath) / name
            rel = full.relative_to(docs_root).as_posix()
            full_real = os.path.realpath(str(full))
            # Resolve containment BEFORE `is_file`: that call follows a symlink,
            # so the earlier ordering stat-ed an external target before the
            # subsequent realpath guard refused it.
            if not _inside(full_real):
                refused_targets.append(rel)
                continue
            try:
                if not full.is_file():
                    continue
            except OSError:
                continue
            if not excluded(rel, patterns):
                survivors.append(rel)
    # MkDocs' `get_files` drops `README.md` when `index.md` sits beside it,
    # because both render to the same `dest_uri`. Reporting both made the audit
    # claim a page the built site does not contain, and `mkdocs build --strict`
    # fails on a nav entry or link pointing at the dropped one.
    by_dir: dict = {}
    for rel in survivors:
        parent = rel.rsplit("/", 1)[0] if "/" in rel else ""
        by_dir.setdefault(parent, set()).add(rel.rsplit("/", 1)[-1])
    shadowed = {
        (parent + "/" if parent else "") + "README.md"
        for parent, names in by_dir.items()
        if "README.md" in names and "index.md" in names
    }
    survivors = [rel for rel in survivors if rel not in shadowed]
    return sorted(survivors)


def page_links(text: str) -> "list[str]":
    """Relative link hrefs on one page, using the framework's own rules.

    Extraction and normalization are `wave_lint_lib.link_validators`': fences and
    inline code stripped first, image links excluded by its regex, schemes and
    pure anchors skipped, fragments stripped, directory links skipped, and the
    href URL-decoded. The decode is load-bearing rather than cosmetic: without it
    a percent-encoded filename reads as a dangling link.

    TWO deliberate divergences from `check_markdown_links`, both because the
    question differs (docs-lint asks "does this repository file exist"; the audit
    asks "does this link resolve to a PUBLISHED page"):

    1. A target outside the root is a finding here and is ignored there.
    2. `link_validators._SKIP_PREFIXES` (`docs/reports/`, `docs/waves/00000 `)
       suppresses whole files from link checking in docs-lint; the audit applies
       no equivalent, because a target whose `exclude_docs` publishes those trees
       needs its links checked like any other published page.

    The shared primitives are imported rather than copied so extraction stays in
    step; the normalization below is this module's own. A normalization rule added
    to `check_markdown_links` (angle-bracket hrefs, query-string stripping, a
    scheme needing more than a prefix match) does NOT reach here automatically,
    which is the known cost of the fork.
    """
    from wave_lint_lib import link_validators as lv  # noqa: PLC0415
    from urllib.parse import unquote  # noqa: PLC0415

    hrefs: list[str] = []
    seen: set[str] = set()
    for match in lv._LINK_RE.finditer(lv._strip_code(text)):
        href = match.group(1).strip()
        if not href or href.startswith("#"):
            continue
        if any(href.startswith(scheme) for scheme in lv._SKIP_SCHEMES):
            continue
        href_path = href.split("#")[0]
        if not href_path or href_path.endswith("/"):
            continue
        href_path = unquote(href_path)
        if href_path in seen:
            continue
        seen.add(href_path)
        hrefs.append(href_path)
    return hrefs


def _headings(text: str) -> "list[str]":
    return [line.strip() for line in text.splitlines() if line.lstrip().startswith("#")]


def _is_subsequence(needle: "list[str]", haystack: "list[str]") -> "list[str]":
    """Return the needle entries missing from *haystack* in order."""
    missing: list[str] = []
    index = 0
    for item in needle:
        found = False
        while index < len(haystack):
            if haystack[index] == item:
                found = True
                index += 1
                break
            index += 1
        if not found:
            missing.append(item)
    return missing


# ---------------------------------------------------------------------------
# Audience baseline. Every git read routes through the sanctioned wrapper.
# ---------------------------------------------------------------------------


def _baseline_text(repo_root: Path, ref: str, rel: str) -> "tuple[str | None, str]":
    """Return (text, degrade_token). text is None when no baseline is available.

    Reads through ``index_state_store._batch_git_blobs``, which fails closed on a
    real git error while treating a missing object as legitimate absence. A bare
    ``git show`` conflated those two states and was removed for it, and this
    check needs exactly that distinction.
    """
    import index_state_store as iss  # noqa: PLC0415

    state, _head = iss._git_authority(repo_root)
    if state != "git":
        return None, DEGRADE_GIT_UNAVAILABLE

    spec = f"{ref}:{rel}"
    blobs = iss._batch_git_blobs(repo_root, [spec])
    if blobs is None:
        return None, DEGRADE_GIT_UNAVAILABLE
    exists, text = blobs.get(spec, (False, ""))
    if exists:
        return text, ""

    # Absent at the ref: distinguish "never committed" from "deleted/renamed",
    # because a freshly generated docs page is untracked and a last-commit
    # lookup on it returns an empty ref that must never reach git.
    try:
        result = iss._run_git(
            ["git", "-C", str(repo_root), "log", "-1", "--format=%H", "--", rel],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        return None, DEGRADE_GIT_UNAVAILABLE
    if result.returncode != 0:
        return None, DEGRADE_GIT_UNAVAILABLE
    if not (result.stdout or "").strip():
        return None, DEGRADE_BASELINE_UNTRACKED
    return None, DEGRADE_BASELINE_MISSING


def _ref_refused(ref: str) -> bool:
    """True when a caller-supplied git ref must be refused before any argv.

    Enumerating separators kept failing one shape at a time: a leading dash was
    the first guard, then `\n` and `\r` were added after `HEAD\n--help` turned a
    real finding into a clean verdict, and then NUL walked through the same way.
    NUL is the worst of them: git truncates the spec at the C-string boundary,
    `cat-file --batch` returns the commit object instead of the blob, no headings
    parse, and the empty sequence trivially satisfies the subsequence check, so
    the report claims `preserved: true` over destroyed heading order.

    So this is a property, not a list: refuse a leading dash, ANY C0 control
    character or DEL, and anything that will not encode as UTF-8 (a lone
    surrogate otherwise raises out of the baseline read). Ordinary revision
    syntax -- `HEAD~1`, `HEAD^`, `origin/main`, a raw SHA -- is unaffected.
    """
    if ref.startswith("-"):
        return True
    if any(ch < " " or ch == "\x7f" for ch in ref):
        return True
    try:
        ref.encode("utf-8")
    except UnicodeEncodeError:
        return True
    return False


def audience_report(repo_root: Path, compare_to: "str | None") -> "tuple[dict, list[str], list[Finding]]":
    """Heading-subsequence check for the startup-order docs.

    The baseline is HEAD content by default. Three readiness lanes proved that
    "the last commit that touched the file" is byte-identical to HEAD for that
    path in every repository state, so this check is informative only against an
    UNCOMMITTED authoring edit, which is when the workflow's Step 3 runs. On a
    clean tree it is an identity check, and that is reported as
    ``baseline_identical`` plus the ``audience_not_informative`` degrade rather
    than as a pass.
    """
    ref = (compare_to or "").strip() or "HEAD"
    audience: dict = {}
    degraded: list[str] = []
    findings: list[Finding] = []

    if _ref_refused(ref):
        # Never let a caller-supplied ref be parsed as a git option.
        for rel in STARTUP_ORDER_DOCS:
            audience[rel] = {"checked": False, "baseline_ref": ref, "baseline_identical": False,
                             "preserved": None, "missing_headings": []}
        return audience, [DEGRADE_COMPARE_TO_REFUSED], findings

    for rel in STARTUP_ORDER_DOCS:
        entry = {"checked": False, "baseline_ref": ref, "baseline_identical": False,
                 "preserved": None, "missing_headings": []}
        current_path = repo_root / rel
        if not current_path.is_file():
            entry["degrade"] = DEGRADE_WORKING_TREE_MISSING
            degraded.append(DEGRADE_WORKING_TREE_MISSING)
            audience[rel] = entry
            continue
        current = current_path.read_text(encoding="utf-8", errors="replace")
        baseline, degrade = _baseline_text(repo_root, ref, rel)
        if baseline is None:
            entry["degrade"] = degrade
            degraded.append(degrade)
            audience[rel] = entry
            continue
        if baseline == current:
            entry.update({"checked": True, "baseline_identical": True, "preserved": True})
            degraded.append(DEGRADE_AUDIENCE_NOT_INFORMATIVE)
            audience[rel] = entry
            continue
        missing = _is_subsequence(_headings(baseline), _headings(current))
        entry.update({"checked": True, "preserved": not missing, "missing_headings": missing})
        if missing:
            findings.append(Finding(
                code="techdocs_audience_heading_lost",
                severity=SEVERITY_HIGH,
                path=rel,
                detail=(f"the baseline heading sequence at {ref} is not a subsequence of the current file; "
                        f"missing: {', '.join(missing)}"),
            ))
        audience[rel] = entry
    return audience, degraded, findings


# ---------------------------------------------------------------------------
# The audit.
# ---------------------------------------------------------------------------


def _trio_state(repo_root: Path) -> dict:
    """Per-member ownership, from the one rule the baseline tool uses.

    `techdocs_member_states` is the source rather than `classify_techdocs_baseline`,
    which returns None unless the trio is mixed: using the mixed-only classifier
    for per-member state is the defect wave 1vj4e DEL-2 repaired.
    """
    from render_agent_surfaces import (  # noqa: PLC0415
        classify_techdocs_baseline,
        techdocs_member_states,
    )

    generated, preserved, absent = techdocs_member_states(repo_root)
    members = {}
    for member in generated:
        members[member] = "generated"
    for member in preserved:
        members[member] = "project_owned"
    for member in absent:
        members[member] = "absent"
    return {"members": members, "partial": classify_techdocs_baseline(repo_root)}


def _sort_key(finding: Finding) -> tuple:
    try:
        rank = FINDING_ORDER.index(finding.code)
    except ValueError:
        rank = len(FINDING_ORDER)
    return (rank, finding.path, finding.href)


def audit_techdocs(repo_root: Path, *, compare_to: "str | None" = None) -> TechdocsAuditReport:
    """Audit the TechDocs publication surface. Reads only; never writes."""
    repo_root = Path(repo_root)
    findings: list[Finding] = []
    degraded: list[str] = []

    trio = _trio_state(repo_root)
    if trio["partial"]:
        findings.append(Finding(
            code="techdocs_trio_partial",
            severity=SEVERITY_MEDIUM,
            path=MKDOCS_FILENAME,
            detail=trio["partial"].get("detail", "the Backstage/TechDocs trio is mixed"),
        ))
    if trio["members"].get("docs/index.md") == "generated":
        findings.append(Finding(
            code="techdocs_index_generated",
            severity=SEVERITY_LOW,
            path="docs/index.md",
            detail="the landing page still carries the generated-by marker, so it has not been authored yet",
        ))

    mkdocs_path = repo_root / MKDOCS_FILENAME
    if not mkdocs_path.is_file():
        degraded.append(DEGRADE_MKDOCS_ABSENT)
        # This early return also skips the audience check, which does not depend
        # on mkdocs.yml, so `audience` comes back empty with no per-doc degrade
        # naming why. That is deliberate: `not_applicable` means the whole audit
        # did not apply, and the authoring branch runs it only after the baseline
        # exists. It is the one place the content-keyed exit rule does not fire
        # for something that was not computed, so it is stated here rather than
        # left for a reader to discover from an empty dict.
        return _finish(repo_root, trio, {}, findings, {}, degraded, VERDICT_NOT_APPLICABLE)

    parsed = parse_mkdocs(mkdocs_path.read_text(encoding="utf-8-sig", errors="replace"))
    # utf-8-sig, because MkDocs reads its own config that way: with plain
    # utf-8 a leading BOM binds to the first key name and that key is
    # silently unrecognized while shape_ok stays true.
    if not parsed["shape_ok"]:
        degraded.append(DEGRADE_MKDOCS_SHAPE)

    docs_root = _contained(repo_root, parsed["docs_dir"])
    if docs_root is None or not docs_root.is_dir():
        if docs_root is None:
            degraded.append(DEGRADE_DOCS_DIR_ESCAPES_ROOT)
        else:
            degraded.append(DEGRADE_MKDOCS_SHAPE)
        publication = {"docs_dir": parsed["docs_dir"], "nav": parsed["nav"],
                       "exclude_docs": parsed["exclude_docs"] or [], "survivor_pages": [], "survivor_count": 0}
        audience, audience_degraded, audience_findings = audience_report(repo_root, compare_to)
        findings.extend(audience_findings)
        degraded.extend(audience_degraded)
        return _finish(repo_root, trio, publication, findings, audience, degraded, None)

    patterns = parsed["exclude_docs"]
    refused: list[str] = []
    if patterns is None:
        # A parsed file with no block is NOT an empty boundary: techdocs-cli
        # re-serializes and drops keys outside its allowlist, so treating the
        # absence as "everything survives" would silently publish agent surfaces.
        # Only claim absence when the shape actually parsed: an unreadable block
        # is present but unread, which `mkdocs_shape` already reports.
        if parsed["shape_ok"]:
            degraded.append(DEGRADE_EXCLUDE_DOCS_ABSENT)
        survivors: list[str] = []
    else:
        refused = unsupported_patterns(patterns)
        if refused:
            degraded.append(DEGRADE_MKDOCS_SHAPE)
        if parsed.get("draft_docs_present"):
            degraded.append(DEGRADE_DRAFT_DOCS_PRESENT)
        unsafe_survivor_targets: list[str] = []
        survivors = survivor_pages(repo_root, docs_root, patterns, unsafe_survivor_targets)

    publication = {
        "docs_dir": parsed["docs_dir"],
        "nav": parsed["nav"],
        "exclude_docs": list(patterns or []),
        "survivor_pages": survivors,
        "survivor_count": len(survivors),
    }
    if refused:
        # Name the patterns, not just the fact. `mkdocs_shape` is shared with
        # six other conditions and says only that something was unreadable, so
        # an operator whose block carries twenty patterns had to bisect their
        # own config to find the one that was dropped. Refusal became a PRIMARY
        # mechanism in this change, which is what made that bisect likely
        # enough to be worth a field. Present only when non-empty, like the
        # truncation markers, so its absence is meaningful.
        publication["unsupported_patterns"] = refused
    if patterns is not None and unsafe_survivor_targets:
        publication["unsafe_survivor_targets"] = sorted(set(unsafe_survivor_targets))
        degraded.append(DEGRADE_SURVIVOR_TARGET_ESCAPES_ROOT)

    resolved_repo_root = os.path.realpath(str(repo_root))
    unsafe_nav_targets: list[str] = []
    for entry in parsed["nav"]:
        # Containment BEFORE any filesystem call. `docs_root / "/etc/passwd"` is
        # `/etc/passwd`, which then reported is_file True and excluded False, so
        # neither branch fired and the audit accepted it as a published page
        # while stat-ing outside the root. Decided lexically so nothing outside
        # the boundary is touched even to be rejected.
        rel_nav = PurePosixPath(entry)
        if rel_nav.is_absolute() or ".." in rel_nav.parts:
            findings.append(Finding(
                code="techdocs_nav_target_missing", severity=SEVERITY_HIGH, path=entry,
                detail="the nav entry escapes docs_dir, so it can never be a published page",
            ))
            continue
        # Normalize ONCE, after the lexical containment screen, and score the
        # normalized form everywhere. MkDocs normalizes through
        # `get_file_from_path`, and scoring the raw string diverged from it in
        # both directions: `./index.md` kept a leading `.` segment that the
        # default `.*` exclusion matched, producing a false
        # `techdocs_nav_target_excluded` at the top severity rank against a
        # tree `mkdocs build --strict` accepts; and a `./`-padded entry long
        # enough to pass the subject bound stat-ed True while `excluded()`
        # short-circuited to False, erasing a real finding. Normalizing cannot
        # be used to escape, because the guard above has already refused any
        # entry carrying `..` or an absolute root.
        rel_entry = os.path.normpath(entry).replace(os.sep, "/")
        target = docs_root / rel_entry
        target_real = os.path.realpath(str(target))
        if not (target_real == resolved_repo_root
                or target_real.startswith(resolved_repo_root + os.sep)):
            # MkDocs follows the link, but this repository-bounded reader will
            # not call is_file(), open, or read content on the external target.
            # `realpath` necessarily performs metadata lookup while resolving
            # the symlink; the contract does not pretend otherwise. This is a
            # refusal, not a missing-file finding: name the logical nav entry
            # and make the incomplete boundary explicit through a degrade.
            unsafe_nav_targets.append(entry)
            if DEGRADE_NAV_TARGET_ESCAPES_ROOT not in degraded:
                degraded.append(DEGRADE_NAV_TARGET_ESCAPES_ROOT)
            continue
        try:
            entry_is_file = target.is_file()
        except OSError:
            # A component over the filesystem's name limit raises ENAMETOOLONG,
            # which is NOT in CPython's ignored-error set for `is_file`, so one
            # over-long nav entry turned the whole audit into an error envelope
            # instead of one finding. Unstattable is exactly "no file here".
            entry_is_file = False
        if not entry_is_file:
            findings.append(Finding(
                code="techdocs_nav_target_missing", severity=SEVERITY_HIGH, path=entry,
                detail=f"the nav entry has no file under {parsed['docs_dir']}/",
            ))
        elif patterns is not None and excluded(rel_entry, patterns):
            findings.append(Finding(
                code="techdocs_nav_target_excluded", severity=SEVERITY_HIGH, path=entry,
                detail="the nav entry exists but exclude_docs removes it, so the built site 404s from its own navigation",
            ))

    if unsafe_nav_targets:
        publication["unsafe_nav_targets"] = unsafe_nav_targets

    if patterns is not None:
        findings.extend(_page_findings(
            repo_root, docs_root, survivors, patterns, unsafe_survivor_targets,
        ))

    audience, audience_degraded, audience_findings = audience_report(repo_root, compare_to)
    findings.extend(audience_findings)
    degraded.extend(audience_degraded)
    return _finish(repo_root, trio, publication, findings, audience, degraded, None)


def _page_findings(
    repo_root: Path,
    docs_root: Path,
    survivors: "list[str]",
    patterns: "list[str]",
    unsafe_targets: "list[str]",
) -> "list[Finding]":
    from wave_lint_lib.metadata_validators import check_metadata  # noqa: PLC0415

    out: list[Finding] = []
    resolved_root = os.path.realpath(str(repo_root))
    docs_root_str = os.path.realpath(str(docs_root))
    survivor_set = set(survivors)
    unsafe_files = {target for target in unsafe_targets if not target.endswith("/")}
    unsafe_dirs = tuple(target for target in unsafe_targets if target.endswith("/"))
    for rel in survivors:
        page = docs_root / rel
        for error in check_metadata(repo_root, page):
            out.append(Finding(
                code="techdocs_metadata_incomplete", severity=SEVERITY_MEDIUM, path=rel,
                detail=error.split(": ", 1)[-1] if ": " in error else error,
            ))
        text = page.read_text(encoding="utf-8", errors="replace")
        for href in page_links(text):
            resolved = os.path.abspath(os.path.join(str(page.parent), href))
            inside_root = resolved == resolved_root or resolved.startswith(resolved_root + os.sep)
            inside_docs = resolved == docs_root_str or resolved.startswith(docs_root_str + os.sep)
            if inside_docs:
                target_rel = os.path.relpath(resolved, docs_root_str).replace(os.sep, "/")
                if target_rel in unsafe_files or any(
                    target_rel == prefix[:-1] or target_rel.startswith(prefix)
                    for prefix in unsafe_dirs
                ):
                    out.append(Finding(
                        code="techdocs_link_outside_boundary", severity=SEVERITY_MEDIUM, path=rel,
                        detail=(f"containment refuses {target_rel} because its resolved target "
                                "lies outside the repository root"),
                        href=href,
                    ))
                    continue
                if excluded(target_rel, patterns):
                    out.append(Finding(
                        code="techdocs_link_outside_boundary", severity=SEVERITY_MEDIUM, path=rel,
                        detail=f"exclude_docs removes {target_rel} from the built site, so this link 404s there",
                        href=href,
                    ))
                    continue
            else:
                out.append(Finding(
                    code="techdocs_link_outside_boundary", severity=SEVERITY_MEDIUM, path=rel,
                    detail=("the target lies outside docs_dir, so it is never a site page"
                            if inside_root else "the target lies outside the repository root"),
                    href=href,
                ))
                continue
            if not os.path.lexists(resolved):
                out.append(Finding(
                    code="techdocs_link_missing", severity=SEVERITY_MEDIUM, path=rel,
                    detail="the link resolves to no file", href=href,
                ))
            elif target_rel.endswith(".md") and target_rel not in survivor_set:
                out.append(Finding(
                    code="techdocs_link_outside_boundary", severity=SEVERITY_MEDIUM, path=rel,
                    detail=(f"{target_rel} is not in the computed published page set, "
                            "so this link 404s in the built site"),
                    href=href,
                ))
    return out


def _finish(repo_root, trio, publication, findings, audience, degraded, forced_verdict) -> TechdocsAuditReport:
    ordered = tuple(sorted(findings, key=_sort_key))
    unique_degraded = tuple(dict.fromkeys(degraded))
    if forced_verdict:
        verdict = forced_verdict
    elif ordered:
        verdict = VERDICT_FINDINGS
    elif unique_degraded:
        # A run that could not compute something never reports clean.
        verdict = VERDICT_DEGRADED
    else:
        verdict = VERDICT_CLEAN
    counts: dict = {}
    for finding in ordered:
        counts[finding.code] = counts.get(finding.code, 0) + 1
    return TechdocsAuditReport(
        repo_root=str(repo_root),
        trio=trio,
        publication=publication,
        findings=ordered,
        audience=audience,
        summary={"finding_count": len(ordered), "counts": counts, "verdict": verdict},
        degraded=unique_degraded,
    )


def _timeout_report(repo_root: Path) -> TechdocsAuditReport:
    """Build the timeout envelope without any repository-derived I/O.

    The worker deadline is useful only if the parent does not start another
    filesystem walk after terminating it. Empty report sections mean
    unavailable, with ``audit_timeout`` carrying the reason.
    """
    return _finish(
        Path(repo_root),
        {},
        {},
        [],
        {},
        [DEGRADE_AUDIT_TIMEOUT],
        None,
    )


def run_techdocs_audit(
    repo_root: Path,
    *,
    compare_to: "str | None" = None,
    timeout_seconds: "float | None" = None,
) -> TechdocsAuditReport:
    """Run the read-only audit behind a hard worker deadline.

    ``audit_techdocs`` remains the one implementation. The worker exists because
    a cooperative deadline cannot interrupt a single catastrophic ``re.match``
    and a thread would leave runaway work alive inside the MCP server.
    """
    import subprocess  # noqa: PLC0415
    from subprocess_util import isolated_run, utf8_child_env  # noqa: PLC0415

    budget = TECHDOCS_AUDIT_TIMEOUT_SECONDS if timeout_seconds is None else float(timeout_seconds)
    if budget <= 0:
        raise ValueError("timeout_seconds must be positive")
    request = json.dumps({"repo_root": str(Path(repo_root)), "compare_to": compare_to})
    env = utf8_child_env()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = isolated_run(
            [sys.executable, str(Path(__file__).resolve()), "--worker-json"],
            input=request,
            capture_output=True,
            text=True,
            timeout=budget,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _timeout_report(Path(repo_root))
    if completed.returncode != 0:
        raise RuntimeError(f"TechDocs audit worker exited {completed.returncode}")
    try:
        payload = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError("TechDocs audit worker returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("TechDocs audit worker returned a non-object report")
    return _report_from_dict(payload)


def _worker_main() -> int:
    """Private JSON worker reached only by :func:`run_techdocs_audit`."""
    request = json.loads(sys.stdin.read())
    report = audit_techdocs(
        Path(request["repo_root"]),
        compare_to=request.get("compare_to"),
    )
    sys.stdout.write(json.dumps(report.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through the bounded parent
    if sys.argv[1:] != ["--worker-json"]:
        raise SystemExit("techdocs_audit_lib.py is an internal worker; use `wf techdocs-audit`")
    raise SystemExit(_worker_main())

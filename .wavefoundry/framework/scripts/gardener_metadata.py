"""Canonical recognition and normalization of docs-gardener metadata."""

from __future__ import annotations

import re


GARDENER_DATE_SENTINEL = "Last verified: <gardener-owned-date>"
PROGRESS_LOG_SENTINEL = "<progress-log narration excluded from the review-policy digest>"
_GARDENER_DATE_LINE_RE = re.compile(r"^Last verified:\s+\d{4}-\d{2}-\d{2}\s*$")
_FRONTMATTER_METADATA_RE = re.compile(r"^[A-Za-z][\w .()/-]*:\s")
# `\s*$` rather than `[ \t]*$` so a CRLF checkout's `## Progress Log\r` still
# matches, exactly as `_GARDENER_DATE_LINE_RE` above already tolerates it. The
# splitter below splits on "\n", so the trailing "\r" reaches this pattern.
_PROGRESS_LOG_HEADING_RE = re.compile(r"^##[ \t]+Progress Log\s*$")
_SECTION_HEADING_PREFIX = "## "
_SECTION_HEADING_RE = re.compile(r"^##[ \t]+(?P<name>[^\r\n]+?)\s*$")
_CHECKBOX_LINE_RE = re.compile(r"^(?P<prefix>\s*-\s*\[)(?P<mark>[ x~X])(?P<suffix>\]\s+.*)$")


def is_gardener_date_line(line: str) -> bool:
    """Return whether ``line`` is the one canonical gardener date shape."""

    return _GARDENER_DATE_LINE_RE.fullmatch(line) is not None


def normalize_gardener_date(text: str, *, replacement: str | None) -> str:
    """Replace or remove one canonical leading-frontmatter gardener date.

    Zero matches and ambiguous multiple matches are returned byte-for-byte. The
    leading frontmatter ends at the first line that is neither blank, a level-1
    title, nor a ``Key: value`` metadata line, so body and fenced lookalikes stay
    load-bearing.
    """

    lines = text.split("\n")
    matches: list[int] = []
    in_frontmatter = True
    for index, line in enumerate(lines):
        if not in_frontmatter:
            break
        if is_gardener_date_line(line):
            matches.append(index)
        if line.strip() and not line.startswith("# ") and not _FRONTMATTER_METADATA_RE.match(line):
            in_frontmatter = False
    if len(matches) != 1:
        return text
    index = matches[0]
    if replacement is None:
        del lines[index]
    else:
        lines[index] = replacement
    return "\n".join(lines)


def _fenced_line_flags(lines: list[str]) -> list[bool]:
    """Flag each line that is a fence marker or sits inside a fenced block.

    Mirrors ``commit_provenance._without_fenced_code``: the fence toggles only
    when the marker matches the currently open fence, so a ``~~~`` inside a
    ``` block does not close it.
    """

    flags: list[bool] = []
    fence = ""
    for line in lines:
        stripped = line.lstrip()
        marker = "```" if stripped.startswith("```") else (
            "~~~" if stripped.startswith("~~~") else ""
        )
        if marker:
            flags.append(True)
            fence = "" if fence == marker else marker if not fence else fence
            continue
        flags.append(bool(fence))
    return flags


def normalize_progress_log(text: str, *, replacement: str | None) -> str:
    """Replace or remove the body of the one canonical ``## Progress Log`` section.

    The Progress Log narrates what happened; it states no reviewable claim, so
    the review-policy digest must not move when a repairer records a repair.
    Zero matches and ambiguous multiple matches are returned byte-for-byte, the
    same degrade contract ``normalize_gardener_date`` uses. The heading is
    anchored at line start, the region ends at the next ``## `` heading or end of
    file, and fenced code is skipped so a heading lookalike inside a fence
    neither opens nor closes a region.
    """

    lines = text.split("\n")
    fenced = _fenced_line_flags(lines)
    matches = [
        index
        for index, line in enumerate(lines)
        if not fenced[index] and _PROGRESS_LOG_HEADING_RE.fullmatch(line)
    ]
    if len(matches) != 1:
        return text
    start = matches[0] + 1
    end = len(lines)
    for index in range(start, len(lines)):
        if not fenced[index] and lines[index].startswith(_SECTION_HEADING_PREFIX):
            end = index
            break
    body = [] if replacement is None else [replacement]
    return "\n".join([*lines[:start], *body, *lines[end:]])


def normalize_checkbox_tracking(text: str) -> str:
    """Stabilize completion tracking without hiding an AC contract deferral.

    Only list items in the canonical Acceptance Criteria and Tasks sections are
    considered, and fenced lines are excluded.  An AC ``[~]`` is deliberately
    preserved; all other completion/task markers canonicalize to ``[ ]``.
    """

    lines = text.split("\n")
    fenced = _fenced_line_flags(lines)
    section = ""
    for index, line in enumerate(lines):
        if fenced[index]:
            continue
        heading = _SECTION_HEADING_RE.fullmatch(line)
        if heading:
            section = heading.group("name").strip().lower()
            continue
        if section not in {"acceptance criteria", "tasks"}:
            continue
        match = _CHECKBOX_LINE_RE.match(line)
        if match is None:
            continue
        mark = match.group("mark").lower()
        if section == "acceptance criteria" and mark == "~":
            continue
        lines[index] = f"{match.group('prefix')} {match.group('suffix')}"
    return "\n".join(lines)


def canonical_review_policy_body(body: bytes) -> bytes:
    """Return review-policy bytes with the non-substantive carriers stabilized.

    Three narrow normalizations, and no more: the gardener-owned date line, the
    body of the one canonical ``## Progress Log`` section, and completion-tracking
    checkbox markers in Acceptance Criteria and Tasks. An Acceptance Criteria
    ``[~]`` is deliberately NOT normalized, because an intentional non-delivery
    changes the contract and must supersede the receipt. Every other section, and
    every checkbox LABEL, stays digested byte for byte, so a plan edit still
    supersedes the receipt.
    """

    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return body
    text = normalize_gardener_date(text, replacement=GARDENER_DATE_SENTINEL)
    text = normalize_progress_log(text, replacement=PROGRESS_LOG_SENTINEL)
    text = normalize_checkbox_tracking(text)
    return text.encode("utf-8")


__all__ = [
    "GARDENER_DATE_SENTINEL",
    "PROGRESS_LOG_SENTINEL",
    "canonical_review_policy_body",
    "is_gardener_date_line",
    "normalize_gardener_date",
    "normalize_checkbox_tracking",
    "normalize_progress_log",
]

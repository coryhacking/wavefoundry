"""Shared change-document checklist parser (wave 1zime, change 1zimq).

Stdlib only.  One reading of a change document's checklist for every gate and
lint rule that counts its items: the close-time hard gate
(``lifecycle_gate_support._collect_silent_unchecked_items_for_close``),
Prepare's per-change section gate, docs-lint's AC and task rules and the
``wf_mark_ac`` / ``wf_mark_task`` item lookup.

- ``CHECKLIST_ITEM_RE`` matches a checklist item under any CommonMark list
  marker (``-``, ``*``, ``+``, or one to nine digits followed by ``.`` or
  ``)``), at any indentation, after an optional blockquote prefix (any run of
  ``>``, each optionally followed by spaces or tabs), with a mark of exactly one
  character other than ``]`` (wave 1zls7, 1zltr).  Groups: ``marker``,
  ``mark``, ``text``.  The gates count every marker so an open item is never
  missed; lint and Prepare require the canonical ``-``.  ``[]`` and
  multi-character marks (``[  ]``, ``[ x]``) are not items.
- Only ``x``, ``X`` and ``~`` close an item (``is_open_mark``).  Any other
  single-character mark (``[-]``, ``[/]``) is OPEN: it blocks close, and lint
  and Prepare report it as non-canonical (``is_canonical_mark``).
- ``fenced_line_flags`` sets fenced code aside (backtick and tilde fences, up
  to three spaces of indent, optionally inside a blockquote).  A fence closes
  on the next line carrying a fence of the same character and at least the
  same length with nothing after it but whitespace.  An unterminated fence is
  NOT a fence (fail closed: a stray fence never hides headings or items), and
  a fence opened inside a blockquote ends at the first line that lacks that
  blockquote prefix, which leaves it unterminated.
- ``leading_ac_id`` takes an item's AC id only from the START of its text,
  optionally wrapped in ``**`` or a backtick.  An id cited later in the text
  is not the item's id.
- ``section_bodies`` returns the body of EVERY H2 section whose heading line is
  exactly ``## <heading>`` (trailing whitespace allowed), each running to the
  next H2 heading line (``##`` plus whitespace, up to three spaces of indent)
  outside fenced code.  An empty list means the heading is absent.  Bodies are
  returned raw; ``checklist_items`` and ``unfenced_text`` set their fenced
  lines aside.
- ``near_miss_headings`` names every H2 heading line outside fenced code whose
  title, compared case-insensitively with whitespace collapsed, STARTS with
  ``<heading>`` but which is not exact (``## Tasks (remaining)``,
  ``##  Tasks``, ``## Acceptance criteria``, ``   ## Tasks``).  Such a section
  is non-canonical: the close gate and the mark tools read its items
  (``include_near_miss=True``), and Prepare and docs-lint refuse it.

LF and CRLF documents parse identically: a trailing carriage return is
trailing whitespace on a heading or fence line and is excluded from item text.
"""
from __future__ import annotations

import re
from typing import Iterator, Optional

CANONICAL_MARKER = "-"

# Marks that close an item; every other single-character mark is open.
CLOSED_MARKS = frozenset("xX~")
# The marks the framework writes: open (space) and the closed marks.
CANONICAL_MARKS = frozenset(" ") | CLOSED_MARKS

CHECKLIST_ITEM_RE = re.compile(
    r"^[ \t]*(?:>[ \t]*)*(?P<marker>[-*+]|\d{1,9}[.)])[ \t]+\[(?P<mark>[^\]\r\n])\][ \t]+(?P<text>.+?)[ \t\r]*$",
    re.MULTILINE,
)

# The id character class the AC Priority table parser uses (``AC-[\w\-]+``).
_LEADING_AC_ID_RE = re.compile(
    r"(?:\*\*(?P<bold>AC-[\w\-]+)\*\*|`(?P<code>AC-[\w\-]+)`|(?P<plain>AC-[\w\-]+))"
)

# An H2 heading line: up to three spaces of indent, ``##``, whitespace, title.
_H2_LINE_RE = re.compile(r"^ {0,3}##[ \t]+(?P<title>.*?)[ \t\r]*$")
_FENCE_OPEN_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_FENCE_CLOSE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})[ \t\r]*$")


def is_canonical_marker(marker: str) -> bool:
    """True for the canonical ``-`` list marker."""
    return marker == CANONICAL_MARKER


def is_open_mark(mark: str) -> bool:
    """True unless ``mark`` is ``x``, ``X`` or ``~`` (an unusual mark is open)."""
    return mark not in CLOSED_MARKS


def is_canonical_mark(mark: str) -> bool:
    """True for the marks the framework writes: space, ``x``, ``X`` and ``~``."""
    return mark in CANONICAL_MARKS


def leading_ac_id(text: str) -> Optional[str]:
    """Return the AC id that STARTS ``text`` (``AC-1: ...``, ``AC-1 (required): ...``,
    ``**AC-1**: ...``, `` `AC-1` ...``), or ``None`` when the text does not start
    with one."""
    match = _LEADING_AC_ID_RE.match(text.lstrip())
    if match is None:
        return None
    return match.group("bold") or match.group("code") or match.group("plain")


def split_blockquote(line: str) -> tuple[int, str]:
    """``(depth, rest)``: the number of blockquote ``>`` markers that prefix
    ``line`` and the text after them (one optional space or tab after each
    marker belongs to the marker).  ``(0, line)`` for an unquoted line."""
    depth = 0
    index = 0
    length = len(line)
    while True:
        probe = index
        while probe < length and line[probe] in " \t":
            probe += 1
        if probe < length and line[probe] == ">":
            depth += 1
            index = probe + 1
            if index < length and line[index] in " \t":
                index += 1
            continue
        return depth, line[index:] if depth else line


def _fence_opener(rest: str) -> Optional[tuple[str, int]]:
    match = _FENCE_OPEN_RE.match(rest)
    if match is None:
        return None
    fence = match.group("fence")
    # CommonMark: a backtick fence's info string cannot contain a backtick.
    if fence[0] == "`" and "`" in match.group("info"):
        return None
    return fence[0], len(fence)


def _closes_fence(rest: str, char: str, length: int) -> bool:
    match = _FENCE_CLOSE_RE.match(rest)
    if match is None:
        return False
    fence = match.group("fence")
    return fence[0] == char and len(fence) >= length


def fenced_line_flags(lines: list[str]) -> list[bool]:
    """Flag each line that opens, closes or sits inside a CLOSED fenced block.

    An unterminated fence flags nothing (its opener and every later line are
    ordinary lines), and a fence opened inside a blockquote is unterminated
    when a line lacking that blockquote prefix comes before its closer.
    """
    flags = [False] * len(lines)
    index = 0
    while index < len(lines):
        depth, rest = split_blockquote(lines[index])
        opener = _fence_opener(rest)
        if opener is None:
            index += 1
            continue
        char, length = opener
        close: Optional[int] = None
        for probe in range(index + 1, len(lines)):
            probe_depth, probe_rest = split_blockquote(lines[probe])
            if probe_depth < depth:
                break
            if probe_depth == depth and _closes_fence(probe_rest, char, length):
                close = probe
                break
        if close is None:
            index += 1
            continue
        for flagged in range(index, close + 1):
            flags[flagged] = True
        index = close + 1
    return flags


def unfenced_text(text: str) -> str:
    """``text`` with every fenced line (fence markers included) blanked."""
    lines = text.split("\n")
    flags = fenced_line_flags(lines)
    return "\n".join("" if fenced else line for line, fenced in zip(lines, flags))


def _h2_title(line: str) -> Optional[str]:
    match = _H2_LINE_RE.match(line)
    return match.group("title") if match else None


def _normalise_title(title: str) -> str:
    return " ".join(title.split()).casefold()


def _is_exact_heading(line: str, heading: str) -> bool:
    return line.rstrip() == f"## {heading}"


def _is_near_miss_heading(line: str, heading: str) -> bool:
    title = _h2_title(line)
    return (
        title is not None
        and _normalise_title(title).startswith(_normalise_title(heading))
        and not _is_exact_heading(line, heading)
    )


def near_miss_headings(text: str, heading: str) -> list[str]:
    """H2 heading lines outside fenced code whose normalised title starts with
    ``<heading>`` but which are not exactly ``## <heading>``."""
    lines = text.split("\n")
    flags = fenced_line_flags(lines)
    return [
        line.rstrip()
        for line, fenced in zip(lines, flags)
        if not fenced and _is_near_miss_heading(line, heading)
    ]


def section_line_indexes(text: str, heading: str, *, include_near_miss: bool = False) -> list[int]:
    """Indexes into ``text.split("\\n")`` of every body line, outside fenced
    code, of every ``## <heading>`` section (and near-miss section with
    ``include_near_miss``), in document order."""
    lines = text.split("\n")
    flags = fenced_line_flags(lines)
    indexes: list[int] = []
    inside = False
    for index, (line, fenced) in enumerate(zip(lines, flags)):
        if fenced:
            continue
        if _h2_title(line) is not None:
            inside = _is_exact_heading(line, heading) or (
                include_near_miss and _is_near_miss_heading(line, heading)
            )
            continue
        if inside:
            indexes.append(index)
    return indexes


def section_bodies(text: str, heading: str, *, include_near_miss: bool = False) -> list[str]:
    """Bodies of every H2 section headed exactly ``## <heading>``; ``[]`` when none.

    With ``include_near_miss`` the bodies of near-miss sections
    (``near_miss_headings``) are included too, in document order.  A ``## ``
    line inside closed fenced code neither ends nor starts a section.
    """
    lines = text.split("\n")
    flags = fenced_line_flags(lines)
    bodies: list[str] = []
    current: Optional[list[str]] = None
    for line, fenced in zip(lines, flags):
        if not fenced and _h2_title(line) is not None:
            if current is not None:
                bodies.append("\n".join(current))
                current = None
            if _is_exact_heading(line, heading) or (
                include_near_miss and _is_near_miss_heading(line, heading)
            ):
                current = []
            continue
        if current is not None:
            current.append(line)
    if current is not None:
        bodies.append("\n".join(current))
    return bodies


def has_section(text: str, heading: str) -> bool:
    """True when ``text`` has at least one H2 heading line exactly ``## <heading>``
    outside fenced code."""
    lines = text.split("\n")
    flags = fenced_line_flags(lines)
    return any(
        not fenced and _is_exact_heading(line, heading) for line, fenced in zip(lines, flags)
    )


def checklist_items(body: str) -> Iterator[re.Match]:
    """Checklist item matches in ``body`` outside fenced code, in order (each
    match is taken on its own line)."""
    lines = body.split("\n")
    for line, fenced in zip(lines, fenced_line_flags(lines)):
        if fenced:
            continue
        match = CHECKLIST_ITEM_RE.match(line)
        if match is not None:
            yield match


def section_items(text: str, heading: str, *, include_near_miss: bool = False) -> Iterator[re.Match]:
    """Checklist item matches across every ``## <heading>`` section, in order."""
    for body in section_bodies(text, heading, include_near_miss=include_near_miss):
        yield from checklist_items(body)


def section_text(text: str, heading: str, *, include_near_miss: bool = False) -> str:
    """Every ``## <heading>`` section body joined, with fenced lines blanked:
    the section as the close gate reads it, for rules that scan it with their
    own patterns."""
    return "\n".join(
        unfenced_text(body)
        for body in section_bodies(text, heading, include_near_miss=include_near_miss)
    )

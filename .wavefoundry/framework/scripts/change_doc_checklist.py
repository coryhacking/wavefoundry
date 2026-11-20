"""Shared spec checklist parser (wave 1zime, change 1zimq).

Stdlib only.  One reading of a spec's checklist for every gate and
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


def _closed_fence_end(
    split: list[tuple[int, str]], index: int, failed_until: dict[tuple[int, str, int], int]
) -> int | None:
    depth, rest = split[index]
    opener = _fence_opener(rest)
    if opener is None:
        return None
    char, length = opener
    key = (depth, char, length)
    if index < failed_until.get(key, -1):
        return None
    stop = len(split)
    for probe in range(index + 1, len(split)):
        probe_depth, probe_rest = split[probe]
        if probe_depth < depth:
            stop = probe
            break
        if probe_depth == depth and _closes_fence(probe_rest, char, length):
            return probe
    failed_until[key] = stop
    return None


def fenced_line_flags(lines: list[str]) -> list[bool]:
    """Flag each line that opens, closes or sits inside a CLOSED fenced block.

    An unterminated fence flags nothing (its opener and every later line are
    ordinary lines), and a fence opened inside a blockquote is unterminated
    when a line lacking that blockquote prefix comes before its closer.

    Complexity (wave 1zyb2, change 1zxnt): each line is split into its
    blockquote depth and text once, and a failed closer scan records, per
    opener key ``(depth, fence character, fence length)``, the line index
    where it stopped (the first depth drop, or the end of the input). A later
    opener with the same key before that index is unterminated without a
    rescan, because its scan window is a suffix of the failed one. Openers
    with ``k`` distinct keys therefore cost at most ``O(k * n)`` line probes.
    Both blockquote depth and fence length are unbounded key components, so
    ``k`` is not a constant: unclosed fences of decreasing length (or
    decreasing depth) make ``k`` grow with ``n`` and cost ``O(n^2)`` line
    probes. Each distinct key needs its own opener line at least as long as
    its fence length and depth, so a set of ``k`` keys spread over both
    dimensions needs about ``k^1.5`` input bytes and ``k`` is ``O(B^(2/3))``
    for ``B`` input bytes (``O(sqrt(B))`` when the keys vary in one dimension
    only). Repeated openers with one key are linear. In general the cost is
    ``O(k * n)`` line probes, at most ``O(B^1.5)``, and each probe matches its
    line, so byte work has the same
    ``O(B^1.5)`` bound (about 5 s for an 8 MB input of 4,000 unclosed fences
    of decreasing length, measured). Real documents use a handful of keys,
    so no attempt is made to beat that bound.
    """
    split = [split_blockquote(line) for line in lines]
    flags = [False] * len(lines)
    # Opener key -> the index at which a failed scan for that key stopped.
    failed_until: dict[tuple[int, str, int], int] = {}
    index = 0
    while index < len(lines):
        close = _closed_fence_end(split, index, failed_until)
        if close is None:
            index += 1
            continue
        for flagged in range(index, close + 1):
            flags[flagged] = True
        index = close + 1
    return flags


_COMMENT_OR_TICKS = re.compile(r"<!--|`+")
_INLINE_BLOCK_START = re.compile(r"^ {0,3}(?:<!--|#{1,6}(?:[ \t]|$)|(?:[-*+]|[0-9]{1,9}[.)])[ \t])")


def comment_visible_lines(lines: list[str], *, tracking_fences: bool = False) -> list[str]:
    """Mask closed HTML comments with spaces, retaining line and character offsets.

    Consume literal code before looking for comment delimiters. Conversely, a
    fence inside a comment is just comment text. The tracking readers retain
    their historical three-character fence toggles; checklist readers require
    a closed fence. An unterminated comment cannot discard later obligations.
    """
    if not any("<!--" in line for line in lines):
        return lines
    last_close = next((i for i in range(len(lines) - 1, -1, -1) if "-->" in lines[i]), -1)
    if last_close < 0:
        return lines
    visible = lines.copy()
    split = [split_blockquote(line) for line in lines]
    # A matching backtick run delimits a code span. Precompute the next run
    # of each width within its paragraph, so unmatched runs cost one lookup.
    next_run = {}
    following = {}
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]
        rest = split[i][1]
        if not rest.strip() or _fence_opener(rest):
            following.clear()
            continue
        # An ATX heading has no continuation lines. Pair its ticks only
        # within the heading; ordinary paragraphs may span soft line breaks.
        if re.match(r"^ {0,3}#{1,6}(?:[ \t]|$)", rest):
            following.clear()
        for ticks in reversed(list(re.finditer(r"`+", line))):
            width = ticks.end() - ticks.start()
            next_run[i, ticks.start()] = following.get(width)
            following[width] = (i, ticks.end())
        # The next paragraph, HTML block, heading or list item cannot
        # supply a closing backtick for a previous block.
        if _INLINE_BLOCK_START.match(rest):
            following.clear()
    in_comment = False
    code_end = None
    fence_end = -1
    tracking_marker = ""
    failed_until = {}
    for i, line in enumerate(lines):
        if i > last_close:
            break
        if i <= fence_end:
            continue
        if not in_comment:
            if tracking_fences:
                start = line.lstrip()[:3]
                if start in ("```", "~~~"):
                    tracking_marker = "" if tracking_marker == start else tracking_marker or start
                    code_end = None
                    continue
                if tracking_marker:
                    continue
            else:
                end = _closed_fence_end(split, i, failed_until)
                if end is not None:
                    fence_end = end
                    code_end = None
                    continue
        pos = 0
        pieces: list[str] = []
        copied = 0
        if code_end is not None:
            if i < code_end[0]:
                continue
            pos = code_end[1]
            code_end = None
        while pos < len(line):
            if not in_comment:
                token = _COMMENT_OR_TICKS.search(line, pos)
                if token is None:
                    break
                pos = token.end()
                if token[0] != "<!--":
                    end = next_run.get((i, token.start()))
                    if end is not None:
                        if end[0] > i:
                            code_end = end
                            break
                        pos = end[1]
                    continue
                start = token.start()
            else:
                start = pos
            close = line.find("-->", pos)
            if close < 0 and i == last_close:
                break
            in_comment = close < 0
            pos = len(line) if in_comment else close + 3
            pieces.extend((line[copied:start], " " * (pos - start)))
            copied = pos
        if pieces:
            pieces.append(line[copied:])
            visible[i] = "".join(pieces)
    return visible


def comment_visible_text(text: str) -> str:
    """Return a position-preserving view for whole-document section searches."""
    if "<!--" not in text or "-->" not in text:
        return text
    return "\n".join(comment_visible_lines(text.split("\n")))


def unfenced_text(text: str) -> str:
    """``text`` with every fenced line (fence markers included) blanked."""
    lines = comment_visible_lines(text.split("\n"))
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
    lines = comment_visible_lines(text.split("\n"))
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
    lines = comment_visible_lines(text.split("\n"))
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
    lines = comment_visible_lines(text.split("\n"))
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
    lines = comment_visible_lines(text.split("\n"))
    flags = fenced_line_flags(lines)
    return any(
        not fenced and _is_exact_heading(line, heading) for line, fenced in zip(lines, flags)
    )


def checklist_items(body: str) -> Iterator[re.Match]:
    """Checklist item matches in ``body`` outside fenced code, in order (each
    match is taken on its own line)."""
    lines = comment_visible_lines(body.split("\n"))
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


def item_block_end(lines: list[str], index: int) -> int:
    """One past the last continuation line of the checklist item at ``index``
    (wave 1zls7, 1zltr; shared since 23042): indented, non-blank, non-item,
    non-heading lines at the item's own blockquote depth."""
    depth = split_blockquote(lines[index])[0]
    end = index + 1
    for probe in range(index + 1, len(lines)):
        probe_depth, rest = split_blockquote(lines[probe])
        if probe_depth != depth or not rest.strip():
            break
        if CHECKLIST_ITEM_RE.match(lines[probe]) or rest.lstrip().startswith("#"):
            break
        if not rest.startswith((" ", "\t")):
            break
        end = probe + 1
    return end


def section_text(text: str, heading: str, *, include_near_miss: bool = False) -> str:
    """Every ``## <heading>`` section body joined, with fenced lines blanked:
    the section as the close gate reads it, for rules that scan it with their
    own patterns."""
    return "\n".join(
        unfenced_text(body)
        for body in section_bodies(text, heading, include_near_miss=include_near_miss)
    )

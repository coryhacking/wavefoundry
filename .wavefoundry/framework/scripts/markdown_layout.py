"""Markdown layout repairs applied to a record's own documents (change 22y1k).

One rule: a heading has an empty line above it. ``ensure_blank_line_before_headings``
inserts the missing line; ``headings_without_blank_line`` reports where one is missing,
for the advisory docs-lint check. Stdlib and ``change_doc_checklist`` only, so prepare,
close and docs-lint can all import it.

A heading is an ATX heading: up to three leading spaces, one to six ``#`` characters,
then a space, a tab or the end of the line (``#tag`` and ``#######`` are not headings).
A line is blank when it is empty or holds only spaces and tabs.
"""
from __future__ import annotations

import re

import change_doc_checklist

_HEADING_RE = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
# The opening marker of a renderer-owned block: ``<!-- x:begin -->`` or
# ``<!-- x:y begin ... -->``. A heading straight after one is the renderer's own
# output, and a line inserted there would make the block differ from its renderer.
_RENDERER_BEGIN_RE = re.compile(
    r"<!--\s*[A-Za-z0-9_.-]+(?::begin\b|(?::[A-Za-z0-9_.-]+)+(?::begin\b|\s+begin\b))"
)


def _is_blank(line: str) -> bool:
    return line.strip(" \t") == ""


def _split_lines(text: str) -> "tuple[list[str], list[str]]":
    """``(lines, endings)``: each line without its ending, and the ending it had
    (``"\\r\\n"``, ``"\\n"`` or ``""`` for a last line with none)."""
    lines: list[str] = []
    endings: list[str] = []
    for raw in text.split("\n"):
        if raw.endswith("\r"):
            lines.append(raw[:-1])
            endings.append("\r\n")
        else:
            lines.append(raw)
            endings.append("\n")
    # The text after the last "\n" has no ending of its own; a "\r" that ends the
    # whole document is put back on that line.
    if endings[-1] == "\r\n":
        lines[-1] += "\r"
    endings[-1] = ""
    return lines, endings


def headings_without_blank_line(text: str, *, include_blockquoted: bool = False) -> list[int]:
    """The 0-based index of each heading whose previous line is not blank.

    Never reported: a heading on the first line, inside a closed fenced block
    (``change_doc_checklist.fenced_line_flags``), or straight after a renderer
    ``begin`` marker. A blockquoted heading is reported only when
    ``include_blockquoted`` is set: the repair leaves blockquotes unchanged, so the
    docs-lint check names them and the repair does not.
    """
    lines, _endings = _split_lines(text)
    fenced = change_doc_checklist.fenced_line_flags(lines)
    found: list[int] = []
    for index in range(1, len(lines)):
        if fenced[index]:
            continue
        depth, rest = change_doc_checklist.split_blockquote(lines[index])
        if depth:
            if not include_blockquoted or not _HEADING_RE.match(rest):
                continue
            _prev_depth, previous = change_doc_checklist.split_blockquote(lines[index - 1])
        else:
            if not _HEADING_RE.match(lines[index]):
                continue
            previous = lines[index - 1]
        if _is_blank(previous):
            continue
        if _RENDERER_BEGIN_RE.match(previous.lstrip(" ")):
            continue
        found.append(index)
    return found


def ensure_blank_line_before_headings(text: str) -> str:
    """Insert one empty line before each heading that follows a non-blank line.

    Keeps the document's line endings: the inserted line takes the ending of the
    line above the heading. Changes nothing else, and applying it twice gives the
    same text as applying it once.
    """
    targets = set(headings_without_blank_line(text))
    if not targets:
        return text
    lines, endings = _split_lines(text)
    out: list[str] = []
    for index, line in enumerate(lines):
        if index in targets:
            out.append(endings[index - 1] or "\n")
        out.append(line + endings[index])
    return "".join(out)

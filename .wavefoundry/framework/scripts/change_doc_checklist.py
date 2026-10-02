"""Shared change-document checklist parser (wave 1zime, change 1zimq).

Stdlib only.  One reading of a change document's checklist for every gate and
lint rule that counts its items: the close-time hard gate
(``lifecycle_gate_support._collect_silent_unchecked_items_for_close``),
Prepare's per-change section gate and docs-lint's AC and task rules.

- ``CHECKLIST_ITEM_RE`` matches a checklist item under any CommonMark list
  marker (``-``, ``*``, ``+``, or one to nine digits followed by ``.`` or
  ``)``), at any indentation, with a ``[ ]``, ``[x]``, ``[X]`` or ``[~]`` mark.
  Groups: ``marker``, ``mark``, ``text``.  The gates count every marker so an
  open item is never missed; lint and Prepare require the canonical ``-``.
- ``leading_ac_id`` takes an item's AC id only from the START of its text,
  optionally wrapped in ``**`` or a backtick.  An id cited later in the text
  is not the item's id.
- ``section_bodies`` returns the body of EVERY H2 section whose heading line is
  exactly ``## <heading>`` (trailing whitespace allowed), each running to the
  next ``## `` line.  An empty list means the heading is absent.
- ``near_miss_headings`` names every H2 heading line that STARTS with
  ``## <heading>`` but is not exact (``## Tasks (remaining)``).  Such a section
  is non-canonical: the close gate counts its items
  (``section_bodies(..., include_near_miss=True)``), and Prepare and docs-lint
  refuse it.

LF and CRLF documents parse identically: a trailing carriage return is
trailing whitespace on a heading line and is excluded from item text.
"""
from __future__ import annotations

import re
from typing import Iterator, Optional

CANONICAL_MARKER = "-"

CHECKLIST_ITEM_RE = re.compile(
    r"^[ \t]*(?P<marker>[-*+]|\d{1,9}[.)])[ \t]+\[(?P<mark>[ xX~])\][ \t]+(?P<text>.+?)[ \t\r]*$",
    re.MULTILINE,
)

# The id character class the AC Priority table parser uses (``AC-[\w\-]+``).
_LEADING_AC_ID_RE = re.compile(
    r"(?:\*\*(?P<bold>AC-[\w\-]+)\*\*|`(?P<code>AC-[\w\-]+)`|(?P<plain>AC-[\w\-]+))"
)


def is_canonical_marker(marker: str) -> bool:
    """True for the canonical ``-`` list marker."""
    return marker == CANONICAL_MARKER


def leading_ac_id(text: str) -> Optional[str]:
    """Return the AC id that STARTS ``text`` (``AC-1: ...``, ``AC-1 (required): ...``,
    ``**AC-1**: ...``, `` `AC-1` ...``), or ``None`` when the text does not start
    with one."""
    match = _LEADING_AC_ID_RE.match(text.lstrip())
    if match is None:
        return None
    return match.group("bold") or match.group("code") or match.group("plain")


def _is_exact_heading(line: str, heading: str) -> bool:
    return line.rstrip() == f"## {heading}"


def _is_near_miss_heading(line: str, heading: str) -> bool:
    return (
        line.startswith("## ")
        and line.rstrip().startswith(f"## {heading}")
        and not _is_exact_heading(line, heading)
    )


def near_miss_headings(text: str, heading: str) -> list[str]:
    """H2 heading lines that start with ``## <heading>`` but are not exact."""
    return [line.rstrip() for line in text.split("\n") if _is_near_miss_heading(line, heading)]


def section_bodies(text: str, heading: str, *, include_near_miss: bool = False) -> list[str]:
    """Bodies of every H2 section headed exactly ``## <heading>``; ``[]`` when none.

    With ``include_near_miss`` the bodies of near-miss sections
    (``near_miss_headings``) are included too, in document order.
    """
    bodies: list[str] = []
    current: Optional[list[str]] = None
    for line in text.split("\n"):
        if line.startswith("## "):
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
    """True when ``text`` has at least one H2 heading line exactly ``## <heading>``."""
    return any(
        _is_exact_heading(line, heading) for line in text.split("\n") if line.startswith("## ")
    )


def section_items(text: str, heading: str, *, include_near_miss: bool = False) -> Iterator[re.Match]:
    """Checklist item matches across every ``## <heading>`` section, in order."""
    for body in section_bodies(text, heading, include_near_miss=include_near_miss):
        yield from CHECKLIST_ITEM_RE.finditer(body)

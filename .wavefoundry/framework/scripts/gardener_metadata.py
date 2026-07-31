"""Canonical recognition and normalization of docs-gardener metadata."""

from __future__ import annotations

import re


GARDENER_DATE_SENTINEL = "Last verified: <gardener-owned-date>"
_GARDENER_DATE_LINE_RE = re.compile(r"^Last verified:\s+\d{4}-\d{2}-\d{2}\s*$")
_FRONTMATTER_METADATA_RE = re.compile(r"^[A-Za-z][\w .()/-]*:\s")


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


def canonical_review_policy_body(body: bytes) -> bytes:
    """Return review-policy bytes with only the gardener-owned date stabilized."""

    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return body
    return normalize_gardener_date(text, replacement=GARDENER_DATE_SENTINEL).encode("utf-8")


__all__ = [
    "GARDENER_DATE_SENTINEL",
    "canonical_review_policy_body",
    "is_gardener_date_line",
    "normalize_gardener_date",
]

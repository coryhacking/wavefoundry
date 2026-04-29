from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from .helpers import read_text, relative_to_root

# Matches [text](href) but NOT image links ![alt](src).
_LINK_RE = re.compile(r"(?<!!)\[(?:[^\[\]]*)\]\(([^)]+)\)")

# Triple-backtick fences (with optional language tag and content).
_CODE_FENCE_RE = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)

# Single-backtick inline code spans (non-greedy, single line).
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")

_SKIP_SCHEMES = ("http://", "https://", "mailto:", "ftp://", "tel://")

# Paths under docs/ that contain historical snapshots; link-checking them produces
# false positives for references to since-deleted files.
_SKIP_PREFIXES = ("docs/reports/", "docs/waves/00000 ")


def _strip_code(text: str) -> str:
    """Remove code fences and inline code to avoid false positives on example links."""
    text = _CODE_FENCE_RE.sub("", text)
    text = _INLINE_CODE_RE.sub("", text)
    return text


def check_markdown_links(root: Path, path: Path) -> list[str]:
    """Return an error for each relative markdown link in *path* that does not resolve."""
    text = read_text(path)
    rel = relative_to_root(root, path)

    if any(rel.startswith(prefix) for prefix in _SKIP_PREFIXES):
        return []

    stripped = _strip_code(text)
    root_resolved = root.resolve()

    failures: list[str] = []
    seen: set[str] = set()

    for match in _LINK_RE.finditer(stripped):
        href = match.group(1).strip()

        # Skip URLs and special schemes.
        if any(href.startswith(s) for s in _SKIP_SCHEMES):
            continue

        # Skip pure anchors.
        if href.startswith("#"):
            continue

        # Skip empty.
        if not href:
            continue

        # Strip fragment; if nothing is left (e.g. href was "#anchor") skip.
        href_path = href.split("#")[0]
        if not href_path:
            continue

        # Skip directory links — trailing slash means the target is a directory,
        # which markdown renderers handle outside our scope.
        if href_path.endswith("/"):
            continue

        # URL-decode percent-encoded characters (e.g. %20 → space in dir names).
        href_path = unquote(href_path)

        # Deduplicate within this file.
        if href_path in seen:
            continue
        seen.add(href_path)

        resolved = (path.parent / href_path).resolve()

        # Skip if it escapes the repo root (shouldn't happen, but be safe).
        try:
            resolved.relative_to(root_resolved)
        except ValueError:
            continue

        if not resolved.exists():
            failures.append(f"{rel}: broken link → {href_path}")

    return failures

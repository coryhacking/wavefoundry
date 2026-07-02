from __future__ import annotations

import os
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
    # Wave 1p9cf: normalize the root ONCE (string level, no per-link realpath). The prior code called
    # Path.resolve() per link — realpath stats every path component and follows symlinks, so link
    # checking was O(link count) × per-syscall filesystem latency and timed out (>30s) on a link-dense
    # doc on a slow filesystem (Windows / WSL2 / network). We only need to know the DECLARED link path
    # stays inside the repo and whether the target exists — both are cheaper and, for a linter, more
    # correct than realpath (we do not want to follow a symlink out of the repo and stat an external path).
    # os.path.abspath is normpath(join(cwd, p)) — it matches resolve()'s absolute/cwd handling WITHOUT the
    # per-component realpath syscalls or symlink following.
    root_norm = os.path.abspath(str(root))
    parent_str = str(path.parent)

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

        # Wave 1p9cf: lexical absolutization (collapses `..`/`.`, cwd-based) instead of realpath.
        resolved = os.path.abspath(os.path.join(parent_str, href_path))

        # Skip if it escapes the repo root (shouldn't happen, but be safe) — a string containment check.
        if resolved != root_norm and not resolved.startswith(root_norm + os.sep):
            continue

        # A single stat (lexists: a present target — including a symlink — is not a broken link).
        if not os.path.lexists(resolved):
            failures.append(f"{rel}: broken link → {href_path}")

    return failures

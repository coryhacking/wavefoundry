from __future__ import annotations

from .constants import METADATA_PATTERNS
from .helpers import read_text, relative_to_root


def check_metadata(root, path) -> list[str]:
    text = read_text(path)
    rel = relative_to_root(root, path)
    if rel.startswith("docs/reports/"):
        return []
    failures: list[str] = []
    for label, pattern in METADATA_PATTERNS.items():
        if not pattern.search(text):
            failures.append(f"{rel}: missing or invalid `{label}` metadata")
    return failures
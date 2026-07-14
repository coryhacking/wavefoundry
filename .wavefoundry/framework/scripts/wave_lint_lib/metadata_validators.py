from __future__ import annotations

from .constants import (
    METADATA_PATTERNS,
    VERIFICATION_STAMP_LINE,
    VERIFICATION_STAMP_VALID,
)
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
    # Verification stamp (1ro43): optional, format-checked only when present.
    # A malformed value silently degrades drift to the content anchor, so the
    # doc would LOOK stamped while carrying no verification meaning — flag it.
    for match in VERIFICATION_STAMP_LINE.finditer(text):
        if not VERIFICATION_STAMP_VALID.match(match.group(0)):
            failures.append(
                f"{rel}: malformed `Verified against` stamp (expected 7-40 hex "
                "chars of a commit SHA, e.g. `Verified against: abc1234`)"
            )
    return failures
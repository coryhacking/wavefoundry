"""Repository machine-authority exclusions shared by retrieval and scan fallback.

Only semantic-walk layers 2–4 live here. File names, extensions, sizes,
ignore patterns and ordinary hidden directories are not scanner exclusions.
"""
from __future__ import annotations

from pathlib import Path

from review_evidence import is_canonical_wave_events_path


HARDCODED_EXCLUDE_PREFIXES = (
    ".wavefoundry/index/",
    ".wavefoundry/framework/index/",
    ".wavefoundry/logs/",
    ".wavefoundry/locks/",
)
HARDCODED_EXCLUDE_PATHS = frozenset({
    ".wavefoundry/guard-overrides.json",
    ".wavefoundry/memory-purge-dispositions.json",
})
MEMORY_ARCHIVE_PREFIX = "docs/agents/memory/archive/"
MEMORY_LEGACY_POINTER_PREFIX = "docs/agents/memory/pointers/"


def is_memory_archive_body_path(rel_path: str) -> bool:
    return rel_path.replace("\\", "/").startswith(MEMORY_ARCHIVE_PREFIX)


def is_legacy_memory_pointer_path(rel_path: str) -> bool:
    return rel_path.replace("\\", "/").startswith(MEMORY_LEGACY_POINTER_PREFIX)


def is_secret_scan_findings_path(rel_path: str) -> bool:
    # Importing wave_lint_lib initializes its CLI, including the scanner that
    # imports this module. Defer the canonical constant until that import ends.
    from wave_lint_lib.constants import SCAN_FINDINGS_PATH

    return rel_path.replace("\\", "/") == SCAN_FINDINGS_PATH


def is_machine_authority_path(rel_path: str, root: Path) -> bool:
    """Match the existing authority paths; never apply general corpus filters."""
    normalized = rel_path.replace("\\", "/")
    return (
        normalized in HARDCODED_EXCLUDE_PATHS
        or is_canonical_wave_events_path(normalized, root)
        or is_memory_archive_body_path(normalized)
        or is_legacy_memory_pointer_path(normalized)
        or is_secret_scan_findings_path(normalized)
        or normalized.startswith(HARDCODED_EXCLUDE_PREFIXES)
    )

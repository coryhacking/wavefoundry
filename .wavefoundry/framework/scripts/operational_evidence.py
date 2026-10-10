"""Retrieval-only exclusions for evidence owned by discovered wave records.

This is deliberately separate from machine_authority: review reads, ledger
access and reconciliation still see these ordinary files.
"""
from __future__ import annotations

import stat
from pathlib import Path

import index_compatibility

index_compatibility.register_loaded_source()

PRIOR_WALKER_VERSION = "16"
WALKER_VERSION = "17"


def discover_operational_evidence(root: Path) -> tuple[set[str], set[str]]:
    """Return excluded directory prefixes and roots whose absence proves nothing.

    Only a discovered record owns its immediate evidence/evidence-* directories.
    Missing or unreadable configured roots cannot authorize removal of old rows.
    Layout errors retain record_paths' fail-closed behavior.
    """
    import record_paths

    roots = record_paths.load_record_roots(root)
    prefixes: set[str] = set()
    protected: set[str] = set()
    for base, rel, discover in (
        (roots.waves, roots.waves_rel, record_paths.discover_wave_dirs),
        (roots.archive, roots.archive_rel, record_paths.discover_archive_dirs),
    ):
        if base is None:
            continue
        try:
            if not record_paths.record_root_is_dir(base, rel):
                protected.add(rel)
                continue
            waves = discover(root, roots)
        except record_paths.RecordRootUnreadable:
            protected.add(rel)
            continue
        for wave in waves:
            try:
                owned: set[str] = set()
                for child in wave.iterdir():
                    if child.name == "evidence" or child.name.startswith("evidence-"):
                        if stat.S_ISDIR(child.lstat().st_mode):
                            owned.add(child.relative_to(root).as_posix() + "/")
                prefixes |= owned
            except OSError:
                protected.add(wave.relative_to(root).as_posix())
    return prefixes, protected


def is_operational_evidence_path(rel: str, prefixes: set[str]) -> bool:
    return rel.replace("\\", "/").startswith(tuple(prefixes))


def filter_operational_evidence(files: list[Path], root: Path,
                                unreadable_dirs: set[str] | None = None) -> list[Path]:
    prefixes, protected = discover_operational_evidence(root)
    if unreadable_dirs is not None:
        unreadable_dirs.update(protected)
    return [path for path in files
            if not is_operational_evidence_path(path.relative_to(root).as_posix(), prefixes)]

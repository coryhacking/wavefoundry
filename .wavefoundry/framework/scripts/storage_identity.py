"""Pure cross-run storage continuity checks; callers retain path/role ownership.

Device numbers are historical evidence, not durable volume identifiers. Matching
paths and available inodes cannot distinguish a replacement volume reusing an
inode. Zero inode on either side further weakens the check to path alone.
Do not use this helper for within-run races or persisted-to-persisted bindings.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


def same_path(stored: object, live: object) -> bool:
    """Compare resolved locators using platform case rules, without writing."""
    if not isinstance(stored, (str, os.PathLike)) or not isinstance(live, (str, os.PathLike)):
        return False
    if not os.fspath(stored) or not os.fspath(live):
        return False
    try:
        return os.path.normcase(str(Path(stored).resolve())) == os.path.normcase(str(Path(live).resolve()))
    except (OSError, ValueError, RuntimeError, TypeError):
        return False


def compare_identity(stored: object, live: object) -> dict:
    """Report continuity, assuming the caller has validated locator/owned role.

Missing or malformed fields are invalid, never an unavailable-inode fallback.
The returned diagnostics are separate from both input mappings.
"""
    def valid(value: object) -> bool:
        return isinstance(value, Mapping) and all(
            type(value.get(key)) is int and value[key] >= 0
            for key in ("device", "inode")
        )

    if not valid(stored) or not valid(live):
        return {"matches": False, "basis": "invalid", "device_drift": False}
    available = bool(stored["inode"] and live["inode"])
    return {
        "matches": not available or stored["inode"] == live["inode"],
        "basis": "path+inode" if available else "path",
        "device_drift": stored["device"] != live["device"],
    }

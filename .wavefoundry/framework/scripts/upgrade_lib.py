#!/usr/bin/env python3
"""Upgrade lock-file utilities shared by upgrade_wavefoundry, dashboard_server, and server.

The upgrade lock file lives at .wavefoundry/upgrade-in-progress.json and prevents the
dashboard from triggering index rebuilds while the framework tree is in a
partially-replaced state.  A lock file (rather than an in-memory flag) survives
dashboard restarts and is inspectable by humans and scripts.
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any

UPGRADE_LOCK_FILENAME = "upgrade-in-progress.json"


def upgrade_lock_path(root: Path) -> Path:
    """Return the canonical path for the upgrade lock file."""
    return root / ".wavefoundry" / UPGRADE_LOCK_FILENAME


def read_upgrade_lock(root: Path) -> dict[str, Any] | None:
    """Return the lock file contents, or None if no lock is present.

    Returns an empty dict (truthy for 'lock present') on read/parse errors so
    callers treat a corrupt lock conservatively — assume upgrade is in progress.
    """
    p = upgrade_lock_path(root)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}  # Corrupt but present — treat as locked.


def write_upgrade_lock(
    root: Path,
    from_version: str | None,
    to_version: str,
    zip_path: Path | None = None,
) -> Path:
    """Write the upgrade lock file and return its path.

    ``zip_path`` (optional) records which zip was used so that standalone
    ``--rebuild-index`` and ``--cleanup`` invocations can reload the same
    extension module rather than guessing from whatever zip is currently on disk.

    Raises OSError if the file cannot be written.
    """
    p = upgrade_lock_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "from_version": from_version,
        "to_version": to_version,
        "pid": os.getpid(),
        "zip_path": str(zip_path) if zip_path is not None else None,
        "pruned_count": None,  # updated after phase 2 via update_upgrade_lock
        # Failure markers (wave 1p44o) — seeded None and populated via
        # update_upgrade_lock when a post-mutation upgrade phase fails, so the
        # lock is RETAINED on a half-replaced tree rather than torn down. A
        # non-null failed_phase signals downstreams (dashboard watcher,
        # --cleanup/resume) that the tree is in a known-failed state.
        "failed_phase": None,
        "failed_at": None,
    }
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return p


def update_upgrade_lock(root: Path, **fields: Any) -> bool:
    """Merge *fields* into the existing lock file and write it back.

    Returns True if the lock was found and updated, False if no lock is present.
    A missing lock is treated as a no-op rather than an error so callers don't
    need to guard against the lock being removed concurrently.
    """
    lock = read_upgrade_lock(root)
    if lock is None:
        return False
    lock.update(fields)
    p = upgrade_lock_path(root)
    try:
        p.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def remove_upgrade_lock(root: Path) -> bool:
    """Remove the upgrade lock file.  Returns True if removed, False if not present."""
    p = upgrade_lock_path(root)
    try:
        p.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def is_lock_stale(root: Path) -> bool:
    """Return True if a lock file exists but the recorded PID is no longer running.

    Stale locks arise when an upgrade script crashes without running cleanup.
    Callers can use this to auto-clear stale locks rather than blocking indefinitely.
    """
    lock = read_upgrade_lock(root)
    if lock is None:
        return False
    pid = lock.get("pid")
    if not isinstance(pid, int) or pid <= 0:
        return True  # Malformed — treat as stale.
    return not _pid_is_running(pid)


def _pid_is_running(pid: int) -> bool:
    """Cross-platform check: return True if *pid* refers to a running process."""
    if os.name == "nt":
        import subprocess
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(pid) in result.stdout
        except OSError:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # Process exists but we can't signal it.
        except OSError:
            return False

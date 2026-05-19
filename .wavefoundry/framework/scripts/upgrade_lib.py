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
) -> Path:
    """Write the upgrade lock file and return its path.

    Raises OSError if the file cannot be written.
    """
    p = upgrade_lock_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "from_version": from_version,
        "to_version": to_version,
        "pid": os.getpid(),
    }
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return p


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

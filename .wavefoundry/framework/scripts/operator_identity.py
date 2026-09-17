"""Best-effort contributor attribution for review events; never an identity gate."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


def resolve_operator(
    root: Path, explicit_handle: str | None = None,
) -> tuple[dict[str, str] | None, str]:
    """Resolve a configured handle without persisting names, emails, or failures.

    Missing configuration is silent to callers; every other unresolved reason
    can be shown as a warning. Explicit selections never fall back to Git.
    """
    try:
        contributors = json.loads(
            (Path(root) / "docs" / "contributors.json").read_text(encoding="utf-8")
        )
    except FileNotFoundError:
        return None, "no_contributors_file"
    except (OSError, UnicodeError):
        return None, "contributors file could not be read"
    except (ValueError, RecursionError):
        return None, "contributors file is not valid JSON"

    if not isinstance(contributors, dict):
        return None, "contributors map has an invalid shape"
    for handle, entry in contributors.items():
        if (
            not isinstance(handle, str) or not handle.strip()
            or not isinstance(entry, dict)
            or not isinstance(entry.get("name"), str) or not entry["name"].strip()
            or not isinstance(entry.get("emails"), list) or not entry["emails"]
            or any(not isinstance(email, str) or not email.strip() for email in entry["emails"])
        ):
            return None, "contributors map has an invalid shape"

    if explicit_handle is not None:
        if isinstance(explicit_handle, str) and explicit_handle in contributors:
            return {"handle": explicit_handle, "source": "explicit"}, ""
        return None, "explicit handle is not in the contributors map"

    # Like the repository's sanitized Git runner, ignore location and config
    # injection overrides while retaining normal global/system configuration.
    env = dict(os.environ)
    for key in (
        "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_CEILING_DIRECTORIES",
        "GIT_DISCOVERY_ACROSS_FILESYSTEM", "GIT_CONFIG", "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_COUNT",
    ):
        env.pop(key, None)
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "config", "user.email"],
            capture_output=True, text=True, encoding="utf-8", timeout=10, env=env,
            stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None, "git user.email lookup failed"
    if result.returncode == 1:
        return None, "git user.email is unset"
    if result.returncode != 0:
        return None, "git user.email lookup failed"
    email = result.stdout.strip().casefold()
    if not email:
        return None, "git user.email is unset"
    matches = [
        handle for handle, entry in contributors.items()
        if any(candidate.strip().casefold() == email for candidate in entry["emails"])
    ]
    if len(matches) > 1:
        return None, "git user.email matches multiple contributor handles"
    if not matches:
        return None, "git user.email is not in the contributors map"
    return {"handle": matches[0], "source": "git_email"}, ""

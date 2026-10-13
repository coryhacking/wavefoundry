"""Best-effort contributor and local-account attribution; never an identity gate."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import unicodedata

import subprocess_util


LOCAL_USER_SOURCE = "local_os_account"
LOCAL_USER_MAX_LENGTH = 256


def local_user_name_problem(value: object) -> str | None:
    """Validate account metadata as stored, without normalization or lookup."""
    if not isinstance(value, str) or not value.strip():
        return "must be a non-empty account name"
    if value != value.strip():
        return "must not have surrounding whitespace"
    if len(value) > LOCAL_USER_MAX_LENGTH:
        return f"must be at most {LOCAL_USER_MAX_LENGTH} characters"
    if any(unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
           for char in value):
        return "contains an unsafe account-name character"
    return None


def _windows_local_user_name() -> str:
    """Read the native current account with one fixed-size, non-retrying call."""
    import ctypes
    from ctypes import wintypes

    get_user_name = ctypes.WinDLL("advapi32", use_last_error=True).GetUserNameW
    get_user_name.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    get_user_name.restype = wintypes.BOOL
    capacity = LOCAL_USER_MAX_LENGTH + 1
    buffer = ctypes.create_unicode_buffer(capacity)
    size = wintypes.DWORD(capacity)
    if not get_user_name(buffer, ctypes.byref(size)) or not 1 < size.value <= capacity:
        raise OSError("current account lookup failed")
    return buffer.value


def resolve_local_user() -> tuple[dict[str, str] | None, str]:
    """Best-effort process-account provenance, never human authentication.

    Username environment variables and caller labels are deliberately ignored.
    Failures disclose no native error text, paths, or account data.
    """
    try:
        if os.name == "posix":
            import pwd

            name = pwd.getpwuid(os.geteuid()).pw_name
        elif os.name == "nt":
            name = _windows_local_user_name()
        else:
            return None, "local account lookup is unavailable"
    except (AttributeError, ImportError, KeyError, OSError, TypeError, ValueError):
        return None, "local account lookup is unavailable"
    if local_user_name_problem(name) is not None:
        return None, "local account name is unsafe or exceeds the attribution limit"
    return {"name": name, "source": LOCAL_USER_SOURCE}, ""


def _run_tree_kill(cmd, **kwargs):
    """Run ``cmd`` so a timeout ends its whole process tree (wave 1z8ox).

    The helper is resolved at call time: an upgrade runner may have an older
    ``subprocess_util`` loaded that lacks ``run_with_tree_kill``, so fall back
    to ``isolated_run``.
    """
    run = getattr(subprocess_util, "run_with_tree_kill", None) or subprocess_util.isolated_run
    return run(cmd, **kwargs)


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
        result = _run_tree_kill(
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

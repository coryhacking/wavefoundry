"""The one definition of record-history path components (wave 1zyb2, change 1zxnt).

A file under a directory named by :data:`HISTORY_PATH_COMPONENTS` is history:
docs-lint's agent validators, the agent-surface integrity scan, the renderer's
review-role slug, the upgrade role backfill, the reconcile scanner and the
retrieval demotion classifier all skip (or demote) it through
:func:`is_history_path`.

Stable contract: the members are ``journals`` and ``snapshots``; adding a member
is a behavior change that needs a changelog line. The match is on a whole path
COMPONENT, never a substring, and is case-sensitive. The path given must be
RELATIVE to the scan root, so a checkout that happens to sit under an ancestor
directory with one of these names is not skipped. Hugging Face model-cache
``snapshots`` directories are unrelated and not covered.

Standard library only: docs-lint hosts and an upgrade running old code import
this module fresh.
"""

from __future__ import annotations

from pathlib import PurePath, PurePosixPath, PureWindowsPath

HISTORY_PATH_COMPONENTS: tuple[str, ...] = ("journals", "snapshots")


def is_history_path(relative: "PurePath | str") -> bool:
    """True when a component of ``relative`` names a history directory.

    ``relative`` is a path relative to the scan root, as a ``Path`` or a POSIX
    string (a backslash in a string is not a separator). An absolute,
    rooted or drive-prefixed path is refused with ``ValueError`` rather than
    tested, since its ancestors would decide the answer.
    """
    if isinstance(relative, str):
        path: PurePath = PurePosixPath(relative)
        # A drive or UNC prefix is absolute on Windows even in POSIX spelling.
        anchored = bool(path.anchor or PureWindowsPath(relative).anchor)
    else:
        path = relative
        anchored = bool(path.anchor)
    if anchored:
        raise ValueError("is_history_path takes a path relative to the scan root")
    return any(part in HISTORY_PATH_COMPONENTS for part in path.parts)

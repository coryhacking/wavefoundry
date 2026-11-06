"""Pure checkout-local recovery commands, usable before Python 3.11 validation.

Only the standard library is imported. No probing, activation or command execution.
"""
from __future__ import annotations

import os
import shlex
from pathlib import Path

def repository_launcher_argv(root: Path | str, *arguments: str,
                             windows: bool | None = None) -> list[str]:
    """Build an absolute checkout-local command without executing or probing it."""
    windows = os.name == 'nt' if windows is None else windows
    if windows:
        import ntpath

        launcher = ntpath.join(ntpath.abspath(str(root)), '.wavefoundry', 'bin', 'wf.cmd')
    else:
        launcher = os.path.join(os.path.abspath(os.path.expanduser(str(root))), '.wavefoundry', 'bin', 'wf')
    return [launcher, *arguments]


def command_shell(*, windows=None):
    """Name the dialect used by format_command; OS does not imply caller shell."""
    return "powershell" if (os.name == "nt" if windows is None else windows) else "posix"


def format_command(argv, *, windows=None):
    """Format argv for a named default dialect without executing it."""
    if not argv:
        return "Restart the Wavefoundry host."
    if command_shell(windows=windows) == "powershell":
        return "& " + " ".join("'" + str(arg).replace("'", "''") + "'" for arg in argv)
    return shlex.join([str(arg) for arg in argv])


def setup_recovery(root, *arguments, windows=None):
    """Return a display string and portable argv; no root means no guessed command."""
    if root is None:
        return {"recovery_usage": "Select the repository, then run its local Wavefoundry setup launcher.",
                "recovery_argv": [], "recovery_shell": None}
    argv = repository_launcher_argv(root, "setup", "--root", str(root), *arguments, windows=windows)
    return {"recovery_usage": format_command(argv, windows=windows),
            "recovery_argv": argv, "recovery_shell": command_shell(windows=windows)}


def setup_command(root, *arguments, windows=None):
    return setup_recovery(root, *arguments, windows=windows)["recovery_usage"]

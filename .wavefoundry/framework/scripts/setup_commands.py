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


# PowerShell ends a single-quoted string at any of these five characters, and
# reads each one doubled as a literal: ' (U+0027), U+2018, U+2019, U+201A, U+201B.
_POWERSHELL_SINGLE_QUOTES = ("\u0027", "\u2018", "\u2019", "\u201a", "\u201b")
_POWERSHELL_QUOTE_DOUBLING = str.maketrans({quote: quote * 2 for quote in _POWERSHELL_SINGLE_QUOTES})


def powershell_quote(value) -> str:
    """Single-quote one argument for PowerShell, doubling every single-quote character."""
    return "'" + str(value).translate(_POWERSHELL_QUOTE_DOUBLING) + "'"


def command_shell(*, windows=None):
    """Name the dialect used by format_command; OS does not imply caller shell."""
    return "powershell" if (os.name == "nt" if windows is None else windows) else "posix"


def format_command(argv, *, windows=None):
    """Format argv for a named default dialect without executing it."""
    if not argv:
        return "Restart the Wavefoundry host."
    if command_shell(windows=windows) == "powershell":
        return "& " + " ".join(powershell_quote(arg) for arg in argv)
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

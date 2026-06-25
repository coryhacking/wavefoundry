"""Shared tool-venv bootstrap — the single venv resolver + re-exec (wave 1p7pl).

Stdlib-only by contract. Imported first-line by every framework entry point so the
process re-execs into the shared tool venv *before* any heavy import. This is the
ONE venv-resolution implementation (1p7pb-adr goal B): no other module may compute
the ``Scripts``-vs-``bin`` / ``WAVEFOUNDRY_TOOL_VENV`` venv path — they call the
accessors here. A standing scan test enforces that (the only allowlisted exception
is ``setup``'s pre-venv system-interpreter bootstrap).

Three interpreter tiers (1p7pb-adr):
  1. setup runs on the system interpreter (pre-venv) — the re-exec no-ops because
     the venv does not exist yet, so it never blocks ``setup_index.ensure_deps``
     from creating it.
  2. committed configs name ``python`` (resolvable post-symlink / native on Windows),
     which launches this bootstrap.
  3. every inner/child spawn *after* bootstrap uses ``sys.executable`` (which, once
     re-exec'd, IS the venv Python — an absolute path), never a re-resolved token.

Diagnostics (if any) go to STDERR only: a single stdout byte before the MCP server's
JSON-RPC handshake corrupts it. The re-exec uses ``os.execv`` on POSIX and a
``subprocess`` relay on Windows, where the CRT emulates ``execv`` as
spawn-child-then-exit-parent — that would orphan the host's stdio pipe (the MCP host
sees an immediate crash) and lose the child's exit code.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

__all__ = [
    "tool_venv_base",
    "tool_venv_python",
    "reexec_into_tool_venv",
    "ensure_python_resolves",
    "gui_fallback_mcp_stanza",
]

# Minimum interpreter the committed `command: "python"` launchers require.
MIN_PYTHON_VERSION = (3, 11)


def tool_venv_base() -> Path:
    """The shared tool-venv base — ``WAVEFOUNDRY_TOOL_VENV`` or ``~/.wavefoundry/venv``."""
    return Path(os.environ.get("WAVEFOUNDRY_TOOL_VENV", "~/.wavefoundry/venv")).expanduser()


def _venv_python_relpath(os_name: str | None = None) -> tuple[str, str]:
    """The venv-relative ``(dir, exe)`` for the Python binary, per OS.

    Pure and OS-parameterizable so the Windows branch is unit-testable on POSIX,
    where a concrete ``WindowsPath`` cannot be instantiated.
    """
    name = os.name if os_name is None else os_name
    return ("Scripts", "python.exe") if name == "nt" else ("bin", "python")


def tool_venv_python() -> Path:
    """Absolute path to the tool venv's Python.

    ``Scripts\\python.exe`` on Windows, ``bin/python`` on POSIX. This is the only
    place in the codebase that branches on the venv layout.
    """
    return tool_venv_base().joinpath(*_venv_python_relpath())


def _running_inside_venv(venv_python: Path) -> bool:
    """True if the current interpreter is the tool venv.

    Compares ``sys.prefix`` (not ``sys.executable``): on macOS/Homebrew the venv
    Python is a symlink to the same underlying binary as the system Python, so an
    executable-path comparison gives false positives. ``sys.prefix`` is the venv
    directory inside a venv and the interpreter's install prefix otherwise.
    """
    try:
        return Path(sys.prefix).resolve() == venv_python.parent.parent.resolve()
    except Exception:
        return False


def reexec_into_tool_venv() -> None:
    """Re-exec the current process under the tool-venv Python when needed.

    No-op when the venv does not exist yet (fresh-bootstrap / pre-setup — must never
    block setup from creating it) or when already running from the venv. Otherwise
    replaces the process: ``os.execv`` on POSIX, a stdio-inheriting ``subprocess``
    relay + ``sys.exit`` on Windows.
    """
    venv_python = tool_venv_python()
    if not venv_python.exists():
        return  # Tier 1: venv not built yet — run on the current (system) interpreter.
    if _running_inside_venv(venv_python):
        return  # Already the venv Python — nothing to do (the common case).
    if os.name == "nt":
        result = subprocess.run([str(venv_python), *sys.argv], check=False)
        sys.exit(result.returncode)
    os.execv(str(venv_python), [str(venv_python), *sys.argv])


# ---------------------------------------------------------------------------
# `python` resolution + heal (wave 1p7pm; lives here so it's the single home).
# Called explicitly at setup / render / upgrade (NOT from reexec_into_tool_venv).
# ---------------------------------------------------------------------------

def _interpreter_version(executable: str) -> tuple[int, int] | None:
    """``(major, minor)`` of the interpreter at ``executable``, or None if unqueryable."""
    try:
        result = subprocess.run(
            [executable, "-c", "import sys;print(sys.version_info[0], sys.version_info[1])"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        major, minor = result.stdout.split()[:2]
        return (int(major), int(minor))
    except (ValueError, IndexError):
        return None


def _user_local_bin() -> Path:
    return Path.home() / ".local" / "bin"


def _shell_rc() -> "Path | None":
    """The shell rc to extend PATH in, inferred from ``$SHELL`` (None if unknown)."""
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    if shell.endswith("zsh"):
        return home / ".zshrc"
    if shell.endswith("fish"):
        return home / ".config" / "fish" / "config.fish"
    if shell.endswith("bash"):
        return home / ".bashrc"
    return None


_PATH_MARKER = "# wavefoundry: python symlink dir on PATH"


def _ensure_dir_on_path(directory: Path) -> bool:
    """Ensure ``directory`` is on PATH (idempotently editing the shell rc if needed).

    Returns True when the user must open a new shell for the change to take effect.
    """
    if str(directory) in os.environ.get("PATH", "").split(os.pathsep):
        return False
    rc = _shell_rc()
    if rc is None:
        print(
            f"wavefoundry: add {directory} to your PATH (could not detect a shell rc).",
            file=sys.stderr,
        )
        return True
    line = (
        f'set -gx PATH "{directory}" $PATH'
        if rc.name == "config.fish"
        else f'export PATH="{directory}:$PATH"'
    )
    try:
        existing = rc.read_text(encoding="utf-8") if rc.exists() else ""
        if _PATH_MARKER not in existing:
            rc.parent.mkdir(parents=True, exist_ok=True)
            with rc.open("a", encoding="utf-8") as handle:
                handle.write(f"\n{_PATH_MARKER}\n{line}\n")
    except OSError:
        print(
            f"wavefoundry: could not update {rc}; add {directory} to your PATH manually.",
            file=sys.stderr,
        )
    return True


def ensure_python_resolves(strict: bool = False) -> str:
    """Make the committed ``command: "python"`` resolvable to Python >= 3.11.

    Order (1p7pb-adr): no-op if ``python`` already resolves to >= 3.11; **warn and DO
    NOT clobber** if it resolves to something else (e.g. python2); otherwise, on POSIX,
    create or re-heal ``~/.local/bin/python`` -> ``python3`` and ensure that dir is on
    PATH. Windows verifies only (``python`` is installer-native — no symlink).

    ``strict=True`` (setup) raises ``SystemExit`` when no usable Python 3 exists;
    ``strict=False`` (render/upgrade) warns non-fatally and self-heals. Diagnostics go
    to stderr. Returns a short status string (``ok`` / ``created`` / ``warn_*`` / ``skipped``).

    Setting ``WAVEFOUNDRY_SKIP_PYTHON_HEAL=1`` makes this a complete no-op (returns
    ``"skipped"``) — for CI, sandboxed runs, read-only-home environments, and tests that
    drive the render/setup/upgrade entry points but must NOT mutate the real machine (the
    heal creates a ``~/.local/bin/python`` symlink and may append to the shell rc).
    """
    if os.environ.get("WAVEFOUNDRY_SKIP_PYTHON_HEAL") == "1":
        return "skipped"
    existing = shutil.which("python")
    if existing:
        version = _interpreter_version(existing)
        if version is not None and version >= MIN_PYTHON_VERSION:
            return "ok"
        print(
            f"wavefoundry: `python` resolves to {existing} (version {version}), below "
            f"{MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} — leaving it untouched. Make "
            "`python` a >= 3.11 interpreter for the Wavefoundry MCP launchers.",
            file=sys.stderr,
        )
        return "warn_existing_unusable"

    if os.name == "nt":
        print(
            "wavefoundry: `python` is not on PATH. Install Python 3.11+ from python.org "
            "with 'Add python.exe to PATH' so the MCP launchers resolve.",
            file=sys.stderr,
        )
        if strict:
            raise SystemExit(2)
        return "warn_no_python"

    python3 = shutil.which("python3")
    version3 = _interpreter_version(python3) if python3 else None
    if not python3 or version3 is None or version3 < MIN_PYTHON_VERSION:
        print(
            "wavefoundry: no Python 3.11+ found on PATH (checked `python`, `python3`). "
            "Install Python 3.11+ to run the Wavefoundry MCP server.",
            file=sys.stderr,
        )
        if strict:
            raise SystemExit(2)
        return "warn_no_python"

    link = _user_local_bin() / "python"
    target = Path(python3)
    try:
        link.parent.mkdir(parents=True, exist_ok=True)
        already_correct = link.is_symlink() and link.resolve() == target.resolve()
        if not already_correct:
            if link.is_symlink() or link.exists():
                link.unlink()  # re-heal a dangling / wrong-target symlink
            link.symlink_to(target)
            status = "created"
        else:
            status = "ok"
    except OSError as exc:
        print(f"wavefoundry: could not create the `python` symlink at {link}: {exc}", file=sys.stderr)
        if strict:
            raise SystemExit(2)
        return "warn_symlink_failed"

    new_shell = _ensure_dir_on_path(_user_local_bin())
    if status == "created":
        note = " Open a new shell for the PATH change to take effect." if new_shell else ""
        print(f"wavefoundry: linked `python` -> {target} at {link}.{note}", file=sys.stderr)
    return status


# ---------------------------------------------------------------------------
# GUI-host fallback (wave 1p7pm AC-4/AC-5): the no-PATH-dependency MCP stanza.
# ---------------------------------------------------------------------------

def gui_fallback_mcp_stanza(repo_root: "str | Path") -> dict[str, object]:
    """The absolute-venv-path MCP stanza for GUI-launched hosts that don't inherit the shell PATH.

    The committed configs name the byte-identical ``command: "python"`` (1p7pb-adr), which resolves
    for CLI hosts (they inherit the shell PATH where setup symlinked ``python``). GUI-launched hosts
    (Claude Desktop, Cursor.app) inherit only a minimal launchd/registry PATH, so ``python`` may not
    resolve. This stanza needs NOTHING on PATH: it names the **absolute** tool-venv Python and the
    **absolute** ``server.py`` path. It is **per-machine** (absolute paths) and must NOT be committed —
    it's printed as setup guidance for the operator to paste into a GUI host's MCP config override."""
    repo = Path(repo_root).expanduser().resolve()
    server_py = repo / ".wavefoundry" / "framework" / "scripts" / "server.py"
    return {
        "command": str(tool_venv_python()),
        "args": [str(server_py), "--root", str(repo)],
    }

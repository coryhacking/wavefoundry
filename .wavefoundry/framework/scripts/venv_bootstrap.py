"""Shared tool-venv bootstrap — the single venv resolver + IN-PROCESS activation (wave 1p7pl/1p802).

Stdlib-only by contract. Imported first-line by every framework entry point so the
process **activates** the shared tool venv *before* any heavy import. This is the ONE
venv-resolution implementation (1p7pb-adr goal B): no other module may compute the
``Scripts``-vs-``bin`` / ``WAVEFOUNDRY_TOOL_VENV`` venv path — they call the accessors
here. A standing scan test enforces that (the only allowlisted exception is ``setup``'s
pre-venv system-interpreter bootstrap).

Three interpreter tiers (1p7pb-adr):
  1. setup runs on the system interpreter (pre-venv) — ``activate_tool_venv`` no-ops
     because the venv does not exist yet, so it never blocks ``setup_index.ensure_deps``
     from creating it.
  2. committed configs name ``python`` (resolvable post-symlink / native on Windows),
     which launches this bootstrap; the bootstrap ACTIVATES the venv **in-process**
     (``site.addsitedir`` of the venv's site-packages) — no re-exec, no child process.
  3. every inner/child spawn *after* bootstrap uses ``sys.executable`` (which, after
     in-process activation, stays the *system* interpreter — but each spawned framework
     script self-activates first-line, so it reaches the venv packages too).

Wave 1p802: the previous ``reexec_into_tool_venv`` re-exec'd into the venv interpreter —
``os.execv`` on POSIX (in-place, same PID) but a ``subprocess`` child on Windows (no
in-place exec). An MCP host spawns ONE process and owns its stdio; the Windows child
became a second process holding the same stdout pipe → broken pipe / orphan on reconnect.
In-process activation keeps a SINGLE host-spawned process on every OS while preserving the
byte-identical ``command: "python"``. Trade-off: the re-exec was robust to a Python
version upgrade for free; in-process activation cannot load ABI-incompatible compiled
deps, so a **version guard** fails loud (run ``wf setup`` to rebuild) instead of crashing.

Diagnostics (if any) go to STDERR only: a single stdout byte before the MCP server's
JSON-RPC handshake corrupts it.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # used by ensure_python_resolves' interpreter-version probe (NOT for any re-exec).
import sys
from pathlib import Path

__all__ = [
    "tool_venv_base",
    "tool_venv_python",
    "activate_tool_venv",
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


def _venv_site_packages(venv_base: Path) -> Path:
    """The tool venv's ``site-packages`` directory for the RUNNING interpreter.

    ``<venv>/Lib/site-packages`` on Windows; ``<venv>/lib/pythonX.Y/site-packages`` on
    POSIX (X.Y from ``sys.version_info`` — the interpreter that will import the packages)."""
    if os.name == "nt":
        return venv_base / "Lib" / "site-packages"
    return venv_base / "lib" / f"python{sys.version_info[0]}.{sys.version_info[1]}" / "site-packages"


def _venv_python_version(venv_base: Path) -> "tuple[int, int] | None":
    """The ``(major, minor)`` the venv was built for, parsed from ``<venv>/pyvenv.cfg``.

    Reads the ``version`` / ``version_info`` line. Returns None when the file is absent or the version
    is unparseable — the caller treats None as fail-open ("can't verify the version line — proceed and
    let a genuine ABI mismatch fail at import"). NOTE: ``version =`` is ``major.minor.patch`` only, so
    an ABI variant that shares it (free-threaded ``3.13t`` / debug build) is indistinguishable here."""
    cfg = venv_base / "pyvenv.cfg"
    try:
        text = cfg.read_text(encoding="utf-8")
    except OSError:
        return None
    for raw in text.splitlines():
        key, sep, value = raw.partition("=")
        if not sep:
            continue
        if key.strip().lower() in ("version", "version_info"):
            parts = value.strip().split(".")
            try:
                return (int(parts[0]), int(parts[1]))
            except (IndexError, ValueError):
                return None
    return None


def activate_tool_venv(*, allow_version_mismatch: bool = False) -> None:
    """Activate the shared tool venv IN-PROCESS (wave 1p802) — no re-exec, no child process.

    Prepends the venv's ``site-packages`` to ``sys.path`` via ``site.addsitedir`` (so its
    ``.pth`` files are processed) in the already-running, host-spawned process. This keeps a
    SINGLE process on every OS — the MCP host owns one stdio pipe and one lifecycle — while
    preserving the byte-identical ``command: "python"``.

    No-op when the venv does not exist yet (fresh-bootstrap / pre-setup — must never block
    ``setup_index.ensure_deps`` from creating it) or when already running inside the venv (e.g.
    a child spawned via ``sys.executable`` that IS the venv Python).

    **Version guard:** if the venv was built for a different Python ``(major, minor)`` than the
    running interpreter, its compiled deps (onnxruntime/lancedb/fastembed) are ABI-incompatible —
    print a clear "run ``wf setup``" message to STDERR and ``sys.exit(2)`` rather than activating
    an unloadable site-packages or falling back to the (Windows-broken) re-exec.

    ``allow_version_mismatch=True`` is reserved for setup/repair entry points. It turns that specific
    mismatch into a no-op (no activation) so setup can rebuild the stale venv it just diagnosed.

    Stderr-only diagnostics (a stdout byte before the JSON-RPC handshake corrupts it)."""
    venv_base = tool_venv_base()
    venv_python = tool_venv_python()
    if not venv_python.exists():
        return  # Tier 1: venv not built yet — run on the current (system) interpreter.
    if _running_inside_venv(venv_python):
        return  # Already inside the venv (e.g. a sys.executable-spawned child) — nothing to do.

    # Version guard. Two conscious edges (wave 1p802 review):
    #   - FAIL-OPEN on None: an absent / malformed `pyvenv.cfg` makes _venv_python_version return None,
    #     and we then PROCEED to activate. Deliberate — don't block a valid venv over an unreadable
    #     version line (a stale/odd `pyvenv.cfg` should not be a hard stop when the venv itself works);
    #     a genuinely ABI-broken venv still fails loud at the first compiled-dep import.
    #   - ABI-VARIANT GAP (accepted residual): this compares only (major, minor). A same-minor ABI
    #     variant that shares the `version =` line — e.g. free-threaded `3.13t` or a debug build — is
    #     NOT caught here. Rare (it requires `python` to resolve to a different variant than built the
    #     venv) and not worth abiflags-recording machinery; the variant's import would fail loudly.
    running = sys.version_info[:2]
    built_for = _venv_python_version(venv_base)
    if built_for is not None and built_for != running:
        if allow_version_mismatch:
            return
        print(
            f"wavefoundry: the tool venv was built for Python {built_for[0]}.{built_for[1]} "
            f"but this is {running[0]}.{running[1]} — run `wf setup` to rebuild it.",
            file=sys.stderr,
        )
        sys.exit(2)

    site_packages = _venv_site_packages(venv_base)
    if not site_packages.is_dir():
        print(
            f"wavefoundry: the tool venv site-packages ({site_packages}) is missing — "
            "run `wf setup` to rebuild it.",
            file=sys.stderr,
        )
        sys.exit(2)

    import site

    # Prepend so the venv wins over any bare system site-packages. addsitedir appends, so
    # record the path set before/after and move the new entries to the front of sys.path.
    before = list(sys.path)
    site.addsitedir(str(site_packages))
    added = [p for p in sys.path if p not in before]
    if added:
        for p in added:
            sys.path.remove(p)
        sys.path[0:0] = added


# ---------------------------------------------------------------------------
# `python` resolution + heal (wave 1p7pm; lives here so it's the single home).
# Called explicitly at setup / render / upgrade (NOT from activate_tool_venv).
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

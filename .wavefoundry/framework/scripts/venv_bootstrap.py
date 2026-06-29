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
  2. committed configs name ``python3`` (which the operator has made resolvable on PATH; setup
     VERIFIES it but does not create a shim/symlink — detect + guide, wave 1p88t), which launches
     this bootstrap; the bootstrap ACTIVATES the venv **in-process** (``site.addsitedir`` of the
     venv's site-packages) — no re-exec, no child process.
  3. every inner/child spawn *after* bootstrap uses ``sys.executable`` (which, after
     in-process activation, stays the *system* interpreter — but each spawned framework
     script self-activates first-line, so it reaches the venv packages too).

Wave 1p802: the previous ``reexec_into_tool_venv`` re-exec'd into the venv interpreter —
``os.execv`` on POSIX (in-place, same PID) but a ``subprocess`` child on Windows (no
in-place exec). An MCP host spawns ONE process and owns its stdio; the Windows child
became a second process holding the same stdout pipe → broken pipe / orphan on reconnect.
In-process activation keeps a SINGLE host-spawned process on every OS while preserving the
byte-identical ``command: "python3"``. Trade-off: the re-exec was robust to a Python
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

# Minimum interpreter the committed `command: "python3"` launchers require.
MIN_PYTHON_VERSION = (3, 11)
MCP_PYTHON_COMMAND = "python3"


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
    preserving the byte-identical ``command: "python3"``.

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

_VER_PROBE = "import sys;print(sys.version_info[0], sys.version_info[1])"


def _interpreter_version(executable: str) -> tuple[int, int] | None:
    """``(major, minor)`` of the interpreter resolved from ``executable``, or None if unqueryable.

    ``executable`` may be a bare token (``"python3"``) — the child spawn does its own fresh PATH
    resolution, so this is a genuine "does ``python3`` resolve to a usable interpreter" check.
    """
    try:
        # Wave 1p8gu: isolate stdin (never inherit a blocking stdin) + suppress the console window on
        # Windows. venv_bootstrap is the foundational STDLIB-ONLY module imported first-line by every
        # entry point (a standing scan test enforces no non-stdlib imports), so it CANNOT import the
        # shared subprocess_util helper — it inlines the same two guarantees instead.
        result = subprocess.run(
            [executable, "-c", _VER_PROBE], capture_output=True, text=True, timeout=15,
            check=False, stdin=subprocess.DEVNULL,
            # 1p8gu: inline CREATE_NO_WINDOW (no console flash on Windows; 0 on POSIX). Inlined — not via
            # a local — so the isolation guard's AST kwarg scan sees the no-window token directly.
            creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0),
            encoding="utf-8", errors="replace",  # 1p8gv (review F2): deterministic capture decoding
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


def ensure_python_resolves(strict: bool = False) -> str:
    """Verify the committed ``command: "python3"`` resolves to Python >= 3.11. DETECT + GUIDE only.

    Wavefoundry does **not** mutate the environment to make ``python3`` resolve — no shim, no
    symlink, no PATH edit, no copy into a Python install (operator decision, wave 1p88t; amends ADR
    1p7pb). Cross-platform auto-healing was invasive and fragile (a Windows ``.cmd`` is not
    raw-spawnable; a POSIX symlink still needs PATH cooperation), so setup/render/upgrade only CHECK
    that ``python3`` already resolves and, when it does not, fail closed (strict) or warn (non-strict)
    with concrete, platform-aware guidance. Making ``python3`` resolvable is the operator's step.

    ``strict=True`` (setup) raises ``SystemExit`` when ``python3`` does not resolve to >= 3.11;
    ``strict=False`` (render/upgrade) warns non-fatally. Diagnostics go to stderr. Returns a short
    status string (``ok`` / ``warn_unresolved`` / ``warn_existing_unusable`` / ``skipped``).

    Setting ``WAVEFOUNDRY_SKIP_PYTHON_HEAL=1`` makes this a complete no-op (returns ``"skipped"``).
    """
    if os.environ.get("WAVEFOUNDRY_SKIP_PYTHON_HEAL") == "1":
        return "skipped"

    existing = shutil.which(MCP_PYTHON_COMMAND)
    version = _interpreter_version(MCP_PYTHON_COMMAND) if existing else None
    if existing and version is not None and version >= MIN_PYTHON_VERSION:
        return "ok"

    if existing:
        reason = (
            f"`{MCP_PYTHON_COMMAND}` resolves to {existing} (version {version}), below "
            f"{MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}"
        )
        status = "warn_existing_unusable"
    else:
        reason = f"`{MCP_PYTHON_COMMAND}` does not resolve on PATH"
        status = "warn_unresolved"
    if os.name == "nt":
        how = (
            "make `python3` resolve to Python 3.11+ on PATH — install via Scoop or the Microsoft "
            "Store (both provide a `python3` command), or add your own `python3` to a PATH directory"
        )
    else:
        how = (
            "make `python3` resolve to Python 3.11+ on PATH — install via your package manager "
            "(e.g. Homebrew/apt), or symlink `python3` to your interpreter in a PATH directory"
        )
    print(
        f"wavefoundry: {reason} — the committed `command: \"{MCP_PYTHON_COMMAND}\"` MCP launchers "
        f"need it. Please {how}, then rerun setup. Wavefoundry does not modify your Python "
        "installation or PATH. Alternative: point your MCP host's Wavefoundry config at the absolute "
        "tool-venv Python (the per-machine fallback stanza setup prints) — it needs nothing on PATH.",
        file=sys.stderr,
    )
    if strict:
        raise SystemExit(2)
    return status


# ---------------------------------------------------------------------------
# GUI-host fallback (wave 1p7pm AC-4/AC-5): the no-PATH-dependency MCP stanza.
# ---------------------------------------------------------------------------

def gui_fallback_mcp_stanza(repo_root: "str | Path") -> dict[str, object]:
    """The absolute-venv-path MCP stanza for GUI-launched hosts that don't inherit the shell PATH.

    The committed configs name the byte-identical ``command: "python3"``, which resolves
    for CLI hosts (they inherit the shell PATH where setup ensured ``python3``). GUI-launched hosts
    (Claude Desktop, Cursor.app) inherit only a minimal launchd/registry PATH, so ``python3`` may not
    resolve. This stanza needs NOTHING on PATH: it names the **absolute** tool-venv Python and the
    **absolute** ``server.py`` path. It is **per-machine** (absolute paths) and must NOT be committed —
    it's printed as setup guidance for the operator to paste into a GUI host's MCP config override."""
    repo = Path(repo_root).expanduser().resolve()
    server_py = repo / ".wavefoundry" / "framework" / "scripts" / "server.py"
    return {
        "command": str(tool_venv_python()),
        "args": [str(server_py), "--root", str(repo)],
    }

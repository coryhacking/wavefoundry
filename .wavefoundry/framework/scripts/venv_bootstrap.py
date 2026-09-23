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

import json
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
    running interpreter, its compiled deps (onnxruntime/apsw/fastembed) are ABI-incompatible —
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
# Canonical `python3` resolution and diagnosis (no environment healing).
# Called explicitly at setup / render / upgrade (NOT from activate_tool_venv).
# ---------------------------------------------------------------------------

_VER_PROBE = "import sys,json;print(json.dumps({'version':list(sys.version_info[:2]),'executable':sys.executable}))"


def _probe_interpreter(executable: str) -> dict:
    """Observe one raw-spawn interpreter command; preserve failures without guessing causes."""
    resolved = shutil.which(executable)
    evidence = {"command": executable, "resolved": resolved, "state": "missing"}
    if not resolved:
        return evidence
    try:
        result = subprocess.run(
            [executable, "-I", "-S", "-B", "-c", _VER_PROBE],
            capture_output=True, text=True, timeout=15, check=False,
            stdin=subprocess.DEVNULL,
            creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0),
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        # TimeoutExpired can expose bytes even with text=True. Preserve the
        # child's observations without treating its timeout as an old version.
        for key, output in (("stdout", exc.stdout), ("stderr", exc.stderr)):
            if output is not None:
                evidence[key] = (output.decode("utf-8", errors="replace")
                                 if isinstance(output, bytes) else output)[:2000]
        return {**evidence, "state": "timeout", "detail": "interpreter probe timed out after 15 seconds"}
    except OSError as exc:
        return {**evidence, "state": "launch_error", "detail": str(exc)[:2000]}
    except subprocess.SubprocessError as exc:
        return {**evidence, "state": "probe_error", "detail": str(exc)[:2000]}
    evidence.update(exit_code=result.returncode, stdout=result.stdout[:2000], stderr=result.stderr[:2000])
    if result.returncode != 0:
        return {**evidence, "state": "failed_exit"}
    try:
        data = json.loads(result.stdout)
        version = data["version"]
        identity = data["executable"]
        if (not isinstance(version, list) or len(version) != 2
                or any(type(part) is not int or part < 0 for part in version)
                or not isinstance(identity, str) or not identity):
            raise ValueError("invalid interpreter identity")
    except (ValueError, TypeError, KeyError):
        return {**evidence, "state": "invalid_output"}
    return {**evidence, "version": tuple(version), "executable": identity,
            "state": "ok" if tuple(version) >= MIN_PYTHON_VERSION else "too_old"}


def _format_interpreter_probe(probe: dict) -> str:
    """Bounded observed facts, kept separate from remediation hypotheses."""
    facts = [f"command={probe['command']}", f"resolved={probe['resolved'] or 'not found on PATH'}",
             f"stage={'command resolution' if probe['state'] == 'missing' else 'interpreter execution/version'}",
             f"result={probe['state']}"]
    for key in ("executable", "version", "exit_code", "detail", "stdout", "stderr"):
        if key in probe and probe[key] != "":
            facts.append(f"{key}={probe[key]!r}")
    return "; ".join(facts)


def ensure_python_resolves(strict: bool = False) -> str:
    """DETECT + GUIDE only: canonical python3 must execute and meet the minimum.

    No shim, symlink, PATH write or installation. Setup's strict check cannot
    be bypassed. The legacy WAVEFOUNDRY_SKIP_PYTHON_HEAL opt-out remains only
    for non-strict render/upgrade compatibility; skipped never means ready.
    All diagnostics go to stderr to preserve MCP stdout.
    """
    if not strict and os.environ.get("WAVEFOUNDRY_SKIP_PYTHON_HEAL") == "1":
        return "skipped"
    probe = _probe_interpreter(MCP_PYTHON_COMMAND)
    if probe["state"] == "ok":
        return "ok"
    print("wavefoundry: Python prerequisite failed: " + _format_interpreter_probe(probe), file=sys.stderr)
    if os.name == "nt":
        alternative = _probe_interpreter("python")
        print("wavefoundry: discovery only (not an MCP fallback): "
              + _format_interpreter_probe(alternative), file=sys.stderr)
        print(
            "wavefoundry: On this workstation, inspect PATH and Manage app execution aliases. "
            "A Store redirect or policy denial must be confirmed from the error above; "
            "the underlying cause is otherwise undetermined. Prefer an existing approved "
            "python3 executable/alias and a permitted user PATH repair. If only python.exe "
            "works, ask IT to expose that approved Python as python3; do not assume admin "
            "rights, Store access or Developer Mode. For diagnosis without Python/MCP run "
            'powershell -NoProfile -File ".wavefoundry/framework/scripts/diagnose_python.ps1". '
            "If policy blocks that script, share the observed command/path/error with IT; "
            "do not bypass execution policy.", file=sys.stderr,
        )
    else:
        print("wavefoundry: Inspect PATH and the resolved interpreter; use your approved "
              "package manager or an operator-managed symlink if appropriate. "
              "An execution failure is not proof of an old or absent installation.", file=sys.stderr)
    print(
        'wavefoundry: MCP requires command: "python3". Verify python3 --version reports '
        "Python 3.11 or newer, then verify server.py --dry-run and fully restart the agent host. "
        "Python 3.13+ is recommended. Shell-only aliases and .cmd shims do not establish "
        "raw-spawn readiness. A seeded checkout does not prove workstation readiness; "
        "do not reseed or rebuild indexes to fix command resolution. "
        "Wavefoundry does not modify your Python installation or PATH.", file=sys.stderr,
    )
    if strict:
        raise SystemExit(2)
    return "warn_unresolved" if probe["state"] == "missing" else "warn_existing_unusable"

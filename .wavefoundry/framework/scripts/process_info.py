"""Read-only process information for tool-environment code (ADR 1z9df, wave 1zc7n).

``psutil`` is a required dependency, imported by a loader so that importing this
module never fails. When ``psutil`` cannot be imported, or is older than the
declared floor, the first call that needs it raises ``ProcessInfoUnavailable``
naming ``wf setup``; there is no hand-rolled fallback. A failed import is not
cached, so installing ``psutil`` while a server runs takes effect on the next
call.

The module answers questions and never decides policy: callers map "unknown"
and "unavailable" to what they mean for them. It never signals, kills or
modifies a process.

Code that runs before dependencies are installed, or inside an older upgrade
runner (``venv_bootstrap``, the setup modules before ``ensure_deps``,
``upgrade_lib``, ``dashboard_lib``, ``sqlite_storage_migration`` and the
modules ``upgrade_protocol`` validates), must not import this module at module
level and never imports ``psutil``.
"""
from __future__ import annotations

import importlib
import os
import subprocess
import threading
from pathlib import Path
from typing import Any, Optional

ALIVE = "alive"
DEAD = "dead"
UNKNOWN = "unknown"

_SETUP_HINT = "run `wf setup` to install or repair it"


class ProcessInfoUnavailable(RuntimeError):
    """``psutil`` cannot be used in this process; the message names ``wf setup``."""


_LOCK = threading.Lock()
_PSUTIL: Any = None
# Wave 1zfd9: while MCP startup installs psutil in the background, the module
# is not imported, so the next call after the install loads the installed
# version instead of one already held in this process.
_STARTUP_INSTALL_PENDING: Optional[str] = None


def set_startup_install_pending(message: Optional[str]) -> None:
    """Mark a startup install of ``psutil`` as running (a message) or finished (None)."""
    global _STARTUP_INSTALL_PENDING
    _STARTUP_INSTALL_PENDING = message


def psutil_loaded() -> bool:
    """Whether this process already holds ``psutil`` (a replacement then needs a restart)."""
    return _PSUTIL is not None


def _min_version() -> tuple[int, ...]:
    try:
        from setup_requirements import PSUTIL_MIN_VERSION
    except Exception:  # noqa: BLE001 - the floor is advisory if the constant is missing
        return (0,)
    return tuple(PSUTIL_MIN_VERSION)


def _version_tuple(text: str) -> tuple[int, ...]:
    parts = []
    for piece in str(text).split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def _load() -> Any:
    """Return the ``psutil`` module or raise ``ProcessInfoUnavailable``.

    The single seam tests patch to supply a fake or failing ``psutil``.
    """
    global _PSUTIL
    if _PSUTIL is not None:
        return _PSUTIL
    with _LOCK:
        if _PSUTIL is not None:
            return _PSUTIL
        if _STARTUP_INSTALL_PENDING:
            raise ProcessInfoUnavailable(_STARTUP_INSTALL_PENDING)
        importlib.invalidate_caches()
        try:
            module = importlib.import_module("psutil")
        except Exception as exc:  # noqa: BLE001 - any failure means unavailable
            raise ProcessInfoUnavailable(
                f"psutil could not be imported ({type(exc).__name__}: {exc}); {_SETUP_HINT}"
            ) from exc
        version = getattr(module, "__version__", "0")
        if _version_tuple(version) < _min_version():
            floor = ".".join(str(n) for n in _min_version())
            raise ProcessInfoUnavailable(
                f"psutil {version} is older than the required {floor}; {_SETUP_HINT}"
            )
        _PSUTIL = module
        return module


def available() -> tuple[bool, str]:
    """Whether ``psutil`` can be used, and the version or the reason it cannot."""
    try:
        module = _load()
    except ProcessInfoUnavailable as exc:
        return False, str(exc)
    return True, str(getattr(module, "__version__", "unknown"))


def _error(ps: Any, name: str) -> type:
    value = getattr(ps, name, None)
    return value if isinstance(value, type) else _Never


class _Never(Exception):
    """Placeholder for an exception class a fake ``psutil`` does not define."""


def _process(ps: Any, pid: int) -> Any:
    """``psutil.Process(pid)``: a handle to an existing process, never a spawn.

    The only construction site, so the framework-wide process-pool guard can
    exempt it by name (it is not a ``multiprocessing.Process``).
    """
    return ps.Process(pid)


def pid_state(pid: int) -> str:
    """``alive``, ``dead`` or ``unknown`` for ``pid``; zombie status is separate."""
    if not isinstance(pid, int) or pid <= 0:
        return DEAD
    ps = _load()
    try:
        exists = bool(ps.pid_exists(pid))
    except Exception:  # noqa: BLE001
        return UNKNOWN
    if not exists:
        return DEAD
    try:
        _process(ps, pid)
    except _error(ps, "NoSuchProcess"):
        return DEAD
    except _error(ps, "AccessDenied"):
        return ALIVE  # existence is proven
    except Exception:  # noqa: BLE001
        return ALIVE  # existence is proven; a follow-up probe failed
    return ALIVE


def is_zombie(pid: int) -> Optional[bool]:
    """True for a zombie, False for a live or absent process, None when unknown."""
    if not isinstance(pid, int) or pid <= 0 or os.name == "nt":
        return False
    ps = _load()
    try:
        status = _process(ps, pid).status()
    except _error(ps, "ZombieProcess"):
        return True
    except _error(ps, "NoSuchProcess"):
        return False
    except _error(ps, "AccessDenied"):
        return None
    except Exception:  # noqa: BLE001
        return None
    return status == getattr(ps, "STATUS_ZOMBIE", "zombie")


def _render(argv: list[str]) -> str:
    # Rendered like today's sources, which the root matchers parse:
    # POSIX `ps -o args=` joins with spaces; Windows uses list2cmdline.
    if os.name == "nt":
        return subprocess.list2cmdline(argv)
    return " ".join(argv)


def cmdline(pid: int) -> Optional[str]:
    """The process's command line rendered as a string, or None."""
    if not isinstance(pid, int) or pid <= 0:
        return None
    ps = _load()
    try:
        argv = _process(ps, pid).cmdline()
    except Exception:  # noqa: BLE001 - absent, zombie, access denied or broken
        return None
    if not argv:
        return None
    return _render([str(arg) for arg in argv])


def cwd(pid: int) -> Optional[Path]:
    """The process's working directory, or None."""
    if not isinstance(pid, int) or pid <= 0:
        return None
    ps = _load()
    try:
        value = _process(ps, pid).cwd()
    except Exception:  # noqa: BLE001
        return None
    return Path(value) if value else None


def create_time(pid: int) -> Optional[float]:
    """The process's start time (seconds since the epoch), or None."""
    if not isinstance(pid, int) or pid <= 0:
        return None
    ps = _load()
    try:
        value = _process(ps, pid).create_time()
    except Exception:  # noqa: BLE001
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

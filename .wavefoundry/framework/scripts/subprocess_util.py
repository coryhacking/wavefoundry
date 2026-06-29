#!/usr/bin/env python3
"""Shared subprocess-isolation helpers (wave 1p8gx / change 1p8gu).

ONE source of truth for the two cross-OS subprocess guarantees the framework
needs on every spawn, **regardless of entry point** (the MCP server, the ``wf``
CLI dispatcher, a direct ``python <script>.py`` run, or an agent invoking
``wf <subcommand>``):

1. **No console window on native Windows.** A child ``python.exe`` (or ``git``,
   ``uv``, …) opens its own console window by default when the parent has no
   console of its own. Passing ``CREATE_NO_WINDOW`` suppresses that flash. The
   field defect that motivated this module was a *stack* of flashing console
   windows during a native-Windows 1.9.4 upgrade — one per unisolated child.

2. **No inherited blocking stdin.** A child that inherits the parent's stdin
   blocks the parent when it reads (the upgrade *hang* field defect: a child
   inheriting the host console's stdin). Every spawn detaches stdin via
   ``DEVNULL`` unless the caller explicitly feeds ``input=`` (a PIPE, not the
   inherited stream).

Wave 1p8gv folds the third cross-OS guarantee into the same helpers:

3. **Deterministic UTF-8 capture decoding.** Captured ``text=True`` spawns
   decode child stdout/stderr as UTF-8 with ``errors="replace"`` so non-ASCII
   output (and the structured-summary JSON) decodes consistently across OSes —
   on a cp1252 Windows console the default ANSI codec mangles it.

This module is stdlib-only and import-cheap (it imports ``subprocess`` lazily
inside each call so it never participates in import cycles or slows cold start).
The four pre-existing per-module copies of the no-window logic
(``_no_window_creationflags`` / ``_windows_no_window_flag`` in ``dashboard_lib``,
``provider_policy``, ``wave_lint_lib/secrets_validators``, ``server_impl``) were
consolidated here; those modules now import ``no_window_creationflags``.
"""
from __future__ import annotations

import os
from typing import Any


def no_window_creationflags() -> int:
    """Return ``subprocess.CREATE_NO_WINDOW`` on native Windows, else ``0``.

    ``0`` is the identity flag for ``creationflags`` on POSIX, so callers can pass
    the result unconditionally. ``CREATE_NO_WINDOW`` only exists on the Windows
    ``subprocess`` module, so it is looked up defensively with ``getattr``.
    """
    if os.name != "nt":
        return 0
    import subprocess

    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))


def detached_background_creationflags() -> int:
    """Creationflags for a *background/detached* Windows child.

    ``DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`` — detaches
    the child from the parent's console and process group (so it survives the
    parent and is signalable independently) AND suppresses the console window.
    Returns ``0`` on POSIX, where callers use ``start_new_session=True`` instead.
    """
    if os.name != "nt":
        return 0
    import subprocess

    return int(
        getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )


def isolated_run(cmd: Any, **kwargs: Any):
    """``subprocess.run`` with the cross-OS isolation guarantees applied.

    - ``stdin`` defaults to ``DEVNULL`` (never inherit a blocking stdin). A caller
      that needs to feed the child passes ``input=`` — that uses a PIPE, never the
      inherited stream — and this helper leaves stdin alone in that case.
    - ``creationflags`` gets ``CREATE_NO_WINDOW`` OR-ed in on Windows (preserving
      any flags the caller already passed).
    - When the spawn is captured as text (``text=True``/``capture_output=True``
      and the caller did not pin an ``encoding``), ``encoding="utf-8",
      errors="replace"`` are applied so child output decodes consistently across
      OSes (wave 1p8gv).

    Any kwarg the caller passes wins — this helper only fills the isolation
    defaults that are absent.
    """
    import subprocess

    if "stdin" not in kwargs and "input" not in kwargs:
        kwargs["stdin"] = subprocess.DEVNULL

    flags = no_window_creationflags()
    if flags:
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | flags

    _apply_utf8_capture(kwargs)

    return subprocess.run(cmd, **kwargs)


def isolated_popen(cmd: Any, **kwargs: Any):
    """``subprocess.Popen`` with the cross-OS isolation guarantees applied.

    Same stdin / no-window contract as :func:`isolated_run`. Background launchers
    that redirect ``stdout``/``stderr`` to a log file pass those explicitly — this
    helper does not touch them — and get ``stdin=DEVNULL`` + the *detached*
    Windows creationflags (so the detached child is also window-free). A caller
    that already set ``creationflags`` (e.g. a foreground Popen wanting only
    no-window) has its flags preserved and OR-ed.

    Detach defaults:
    - On Windows: ``creationflags`` gets the detached-background set OR-ed in
      *unless* the caller already passed ``creationflags`` (then only the
      no-window bit is OR-ed, to honor a foreground intent).
    - On POSIX: ``start_new_session=True`` is set unless the caller pinned it.
    """
    import subprocess

    if "stdin" not in kwargs:
        kwargs["stdin"] = subprocess.DEVNULL

    if os.name == "nt":
        if "creationflags" in kwargs:
            kwargs["creationflags"] = kwargs["creationflags"] | no_window_creationflags()
        else:
            kwargs["creationflags"] = detached_background_creationflags()
    else:
        kwargs.setdefault("start_new_session", True)

    _apply_utf8_capture(kwargs)

    return subprocess.Popen(cmd, **kwargs)


def _apply_utf8_capture(kwargs: dict[str, Any]) -> None:
    """Apply ``encoding='utf-8', errors='replace'`` for captured text spawns (wave 1p8gv).

    Only when the spawn decodes to text (``text=True``/``universal_newlines=True``)
    and the caller did not already pin an ``encoding``. Binary spawns (no text mode)
    are left untouched.
    """
    text_mode = kwargs.get("text") or kwargs.get("universal_newlines")
    if not text_mode:
        return
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("errors", "replace")


# ---------------------------------------------------------------------------
# Window-free multiprocessing pools (wave 1p8gx / 1p8gu adversarial-review fix)
# ---------------------------------------------------------------------------
#
# The per-spawn helpers above isolate ``subprocess.run``/``Popen``. They do NOT cover the
# ``ProcessPoolExecutor`` / ``multiprocessing`` POOLS used by the graph extractor, the parallel
# secrets scanner, and the indexer — and the pools were the operator's actual field defect: with the
# ``spawn`` start method on Windows, each worker is launched by ``python.exe`` (the CONSOLE-subsystem
# interpreter) with ``dwCreationFlags=0``, so **every worker opens its own console window** (the
# parent's ``CREATE_NO_WINDOW`` is not inherited by multiprocessing workers).
#
# Fix: point the pool's start method at ``pythonw.exe`` — the WINDOWS-subsystem interpreter, which has
# no console — via ``mp_context.set_executable``. Workers talk over pipes, not a console, so pythonw is
# a drop-in. On POSIX this is a no-op (no console subsystem). If pythonw cannot be located the caller
# should fall back to a thread/serial backend (no separate processes → no windows).


def utf8_child_env(env: "dict[str, str] | None" = None) -> "dict[str, str]":
    """Return a child-process env with UTF-8 stdio forced (wave 1p8gv child-encoding fix).

    Sets ``PYTHONUTF8=1`` and ``PYTHONIOENCODING=utf-8`` so a spawned framework child decodes/encodes
    its OWN stdout/stderr as UTF-8 regardless of the host console codepage. Without this a child that
    ``print``s a non-ASCII glyph (e.g. ``→`` U+2192 in the indexer) raises ``UnicodeEncodeError`` in
    the CHILD on a cp1252 Windows console and the parent only sees a non-zero exit. ``configure_utf8_
    stdio()`` in the child's own ``main`` covers direct invocation; this covers spawned children whose
    main runs before any reconfigure and is belt-and-suspenders for both.

    Starts from ``env`` (or a copy of ``os.environ`` when None). Sets both vars UNCONDITIONALLY: UTF-8
    child stdio is the guarantee, so an inherited ``PYTHONIOENCODING=cp1252`` (which would otherwise win
    over ``PYTHONUTF8``) is deliberately overridden — we never want a framework child encoding its
    stdout as cp1252.
    """
    base = dict(os.environ if env is None else env)
    base["PYTHONUTF8"] = "1"
    base["PYTHONIOENCODING"] = "utf-8"
    return base


def windowless_pythonw() -> "str | None":
    """Return the tool-venv ``pythonw.exe`` path on Windows (console-free), else None.

    Prefers the shared tool venv's ``Scripts/pythonw.exe`` (where the framework runs), then a
    ``pythonw.exe`` next to the current ``sys.executable``. Returns None on POSIX or when no pythonw is
    found (caller should then use a thread/serial backend)."""
    if os.name != "nt":
        return None
    import sys
    from pathlib import Path

    candidates = []
    try:
        import venv_bootstrap  # lazy — avoids any import cycle; subprocess_util is not stdlib-locked

        candidates.append(venv_bootstrap.tool_venv_base() / "Scripts" / "pythonw.exe")
    except Exception:
        pass
    exe = Path(sys.executable)
    candidates.append(exe.with_name("pythonw.exe"))
    candidates.append(exe.parent / "pythonw.exe")
    for cand in candidates:
        try:
            if cand.is_file():
                return str(cand)
        except OSError:
            continue
    return None


def configure_windowless_mp_context(mp_context: Any) -> bool:
    """Make an mp context launch CONSOLE-FREE workers on Windows. Returns True when applied.

    On Windows, sets the context executable to ``pythonw.exe`` (no console) so ``spawn`` workers do not
    each flash a console window. No-op (returns True) on POSIX. Returns False on Windows when no
    pythonw is available — the caller MUST then fall back to a thread/serial backend so the workers do
    not open console windows."""
    if os.name != "nt":
        return True
    pythonw = windowless_pythonw()
    if pythonw is None:
        return False
    try:
        mp_context.set_executable(pythonw)
        return True
    except Exception:
        return False


def windowless_mp_context(start_method: str = "spawn") -> Any:
    """Return a multiprocessing context configured for console-free workers, or None.

    Returns a context with its executable pointed at ``pythonw.exe`` on Windows (console-free), the
    bare context on POSIX, or None when a window-free pool cannot be guaranteed on Windows (no
    pythonw) — in which case the caller MUST use a thread/serial backend instead of a process pool.
    """
    import multiprocessing as mp

    try:
        ctx = mp.get_context(start_method)
    except (ValueError, RuntimeError):
        return None
    if not configure_windowless_mp_context(ctx):
        return None  # Windows without pythonw — signal "do not open a process pool"
    return ctx

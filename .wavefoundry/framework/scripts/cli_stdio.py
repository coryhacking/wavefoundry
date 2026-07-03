#!/usr/bin/env python3
"""Shared CLI stdio UTF-8 reconfigure (wave 1p8gx / change 1p8gv).

ONE source of truth for making a CLI entry point's stdout/stderr able to print
non-ASCII (``⚠`` U+26A0, box-drawing ``──``, …) without raising on a native
Windows ``cp1252`` console.

The MCP runner (``server.py``) already reconfigures its stdio for byte-stable
JSON-RPC framing; this helper generalizes that pattern for the *plain CLI* entry
points (``upgrade_wavefoundry``, ``setup_wavefoundry``, ``wf_cli``,
``docs_gardener``, ``docs_lint``, ``run_secrets_scan``/``scan_secrets``,
``gen_codebase_map``, ``dashboard_server``, ``render_platform_surfaces``). The
field defect that motivated it: a native-Windows 1.9.4 upgrade crashed with
``UnicodeEncodeError`` the first time it ``print("⚠")`` because nothing had
reconfigured stdout to UTF-8.

Best-effort and idempotent: streams without a ``reconfigure`` method (or that
reject options) are skipped silently — a diagnostics helper must never crash the
program it is trying to make robust.
"""
from __future__ import annotations

import contextlib
import os
import sys


@contextlib.contextmanager
def isolated_stdout_fd():
    """Redirect OS-level stdout (file descriptor 1) to ``os.devnull`` for the duration of the block.

    ``contextlib.redirect_stdout`` only swaps the Python ``sys.stdout`` object — it CANNOT intercept
    a C/C++ extension that writes DIRECTLY to fd 1 (e.g. onnxruntime's DirectML EP enumerating GPU
    adapters on its first load). When fd 1 is a stdio JSON-RPC channel (the MCP server's transport),
    those native bytes corrupt the protocol framing and hang the call (wave 1p8vc). This redirects at
    the OS fd level, which catches native writes too. Pair it with ``redirect_stdout(sys.stderr)`` so
    meaningful Python-level output still routes to stderr while native fd-1 noise is dropped.

    Saves and restores fd 1 in a ``finally`` (no fd leak), flushing the Python stdout buffer on both
    sides so buffered Python bytes are not misdirected. Safe no-op when ``sys.stdout`` has no real
    ``fileno()`` (e.g. a captured ``StringIO`` under test). Pure stdlib; ``os.dup``/``os.dup2`` work
    on native Windows. Wrap ONLY synchronous work that must not write to the channel, and let fd 1 be
    restored before anything writes the real response.
    """
    try:
        stdout_fd = sys.stdout.fileno()
    except (AttributeError, OSError, ValueError):
        # No real OS fd behind sys.stdout (redirected/captured stream) — nothing to protect.
        yield
        return
    saved_fd = os.dup(stdout_fd)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        try:
            sys.stdout.flush()
        except Exception:
            pass
        os.dup2(devnull_fd, stdout_fd)
        yield
    finally:
        try:
            sys.stdout.flush()
        except Exception:
            pass
        os.dup2(saved_fd, stdout_fd)
        os.close(saved_fd)
        os.close(devnull_fd)


def configure_utf8_stdio() -> None:
    """Reconfigure ``stdin``/``stdout``/``stderr`` to UTF-8 so non-ASCII never mis-decodes or raises.

    Mirrors ``server.py``'s guarded ``getattr(stream, "reconfigure", None)``
    pattern. Unlike the MCP runner this does NOT pin a newline translation —
    plain CLI output should keep the platform default — it only fixes the
    *encoding* so a cp1252 console can render ``⚠`` / box-drawing characters,
    and so a hook reading a UTF-8 JSON payload from ``stdin`` (a file path,
    message, or diff excerpt carrying box-drawing / accented / em-dash bytes)
    decodes it correctly instead of mis-decoding under the console codepage
    (wave 1p9j0 / change 1p9iv). Streams that are ``None`` or lack a
    ``reconfigure`` method (e.g. a captured ``StringIO`` under test) are skipped
    silently.
    """
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # Some host-provided / redirected stream objects do not support
            # reconfigure options. Never block the program for diagnostics.
            continue

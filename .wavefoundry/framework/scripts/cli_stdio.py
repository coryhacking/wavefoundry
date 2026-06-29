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

import sys


def configure_utf8_stdio() -> None:
    """Reconfigure ``stdout``/``stderr`` to UTF-8 so non-ASCII prints never raise.

    Mirrors ``server.py``'s guarded ``getattr(stream, "reconfigure", None)``
    pattern. Unlike the MCP runner this does NOT pin a newline translation —
    plain CLI output should keep the platform default — it only fixes the
    *encoding* so a cp1252 console can render ``⚠`` / box-drawing characters.
    """
    for stream_name in ("stdout", "stderr"):
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

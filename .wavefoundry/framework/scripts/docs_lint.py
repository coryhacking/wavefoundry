#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

# Change 1zyv1: bytecode goes only to the project cache (``bytecode_cache``),
# never beside the sources; writes stay off until configure() enables the cache.
if __name__ == "__main__" or sys.pycache_prefix is None:
    sys.dont_write_bytecode = True

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import bytecode_cache  # noqa: E402

if __name__ == "__main__":
    bytecode_cache.configure()

import venv_bootstrap  # the single venv resolver (wave 1p7pl)
import cli_stdio  # shared UTF-8 stdio reconfigure (wave 1p8gv)

# Activate the shared tool venv IN-PROCESS before any heavy import (wave 1p7pl/1p802). No-op when
# already in the venv or when it does not exist yet (fresh bootstrap).
venv_bootstrap.activate_tool_venv()
# Wave 1p8gv: CLI entry — UTF-8 stdout/stderr so non-ASCII prints never raise on a cp1252 console.
cli_stdio.configure_utf8_stdio()

from wave_lint_lib.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
